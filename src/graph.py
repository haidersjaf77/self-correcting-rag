"""The self-correcting RAG graph.

Self-correction happens at three checkpoints:
  1. grade_documents : drop irrelevant chunks; if none are left, try to recover
  2. check (grounded) : reject answers with facts not in the documents
  3. check (useful)   : reject answers that don't resolve the question (incl. refusals)
Recovery order (next_fallback): rewrite the query once -> web search once (if allowed) -> refuse.
At most 3 generations per question, so it can never loop forever.

Every node appends a record to state["steps"], so callers (API, UI) can show how an answer was produced.

Command line:
    python -m src.graph "How do AI agents manage memory and context?"
    python -m src.graph "Who won the 2022 FIFA World Cup?" --scoped
"""
import argparse
import logging
import operator
from typing import Annotated, List

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from src import config
from src.components import (
    REFUSAL, answer_grader, format_docs, hallucination_grader, query_rewriter,
    question_router, rag_chain, retrieval_grader, retriever, web_search,
)

log = logging.getLogger(__name__)


class GraphState(TypedDict):
    question: str            # the user's original question (never changes)
    search_query: str        # what we actually search with (may be rewritten)
    generation: str
    documents: List[Document]
    web_searched: bool
    rewrites: int
    answer_source: str       # "knowledge_base", "web", or "none"
    route: str               # router decision: "vectorstore" | "web_search" | "give_up"
    verdict: str             # check decision:  "done" | "rewrite" | "web_search" | "give_up"
    steps: Annotated[List[dict], operator.add]   # appended to by every node, never overwritten


def _step(name: str, **detail) -> list[dict]:
    log.info("%-15s %s", name.upper(), detail)
    return [{"step": name, **detail}]


def build_graph(allow_web_fallback: bool = config.ALLOW_WEB_FALLBACK,
                max_rewrites: int = config.MAX_REWRITES):
    """Compile the graph. The mode is fixed per compiled graph, not read from a global."""

    def next_fallback(state) -> str:
        if state.get("rewrites", 0) < max_rewrites and not state.get("web_searched"):
            return "rewrite"
        if allow_web_fallback and not state.get("web_searched"):
            return "web_search"
        return "give_up"

    # ---------- Nodes (do work, record what happened) ----------

    def route(state):
        decision = question_router.invoke({"question": state["question"]}).datasource
        note = ""
        if decision == "web_search" and not allow_web_fallback:
            decision, note = "give_up", "out of scope and web search is disabled"
        return {"route": decision, "steps": _step("route", decision=decision, note=note)}

    def retrieve(state):
        query = state.get("search_query") or state["question"]
        docs = retriever.invoke(query)
        return {"documents": docs, "steps": _step("retrieve", query=query, found=len(docs))}

    def grade_documents(state):
        relevant, grades = [], []
        for d in state["documents"]:
            grade = retrieval_grader.invoke(
                {"question": state["question"], "document": d.page_content}
            ).binary_score
            grades.append({"source": d.metadata.get("source", "unknown"), "grade": grade})
            if grade == "yes":
                relevant.append(d)
        return {"documents": relevant,
                "steps": _step("grade_documents", kept=len(relevant), grades=grades)}

    def rewrite(state):
        new_query = query_rewriter.invoke({"question": state["question"]}).strip()
        return {"search_query": new_query, "rewrites": state.get("rewrites", 0) + 1,
                "steps": _step("rewrite", new_query=new_query)}

    def web_search_node(state):
        results = web_search(state["question"])
        return {"documents": state.get("documents", []) + results, "web_searched": True,
                "steps": _step("web_search", found=len(results),
                               sources=[d.metadata["source"] for d in results])}

    def generate(state):
        generation = rag_chain.invoke(
            {"context": format_docs(state["documents"]), "question": state["question"]}
        )
        source = "web" if state.get("web_searched") else "knowledge_base"
        return {"generation": generation, "answer_source": source,
                "steps": _step("generate", from_source=source,
                               refused=generation.strip() == REFUSAL)}

    def check(state):
        question, generation = state["question"], state["generation"]
        fallback = next_fallback(state)

        if generation.strip() == REFUSAL:
            return {"verdict": fallback, "steps": _step(
                "check", verdict=fallback, grounded=None, useful=False,
                reason="The model refused: the documents did not contain the answer.")}

        h = hallucination_grader.invoke(
            {"documents": format_docs(state["documents"]), "generation": generation}
        )
        if h.binary_score == "no":
            return {"verdict": fallback, "steps": _step(
                "check", verdict=fallback, grounded=False, useful=None, reason=h.reasoning)}

        useful = answer_grader.invoke({"question": question, "generation": generation}).binary_score == "yes"
        verdict = "done" if useful else fallback
        reason = h.reasoning if useful else "Grounded, but it does not resolve the question."
        return {"verdict": verdict, "steps": _step(
            "check", verdict=verdict, grounded=True, useful=useful, reason=reason)}

    def give_up(state):
        return {"generation": REFUSAL, "answer_source": "none", "steps": _step("give_up")}

    # ---------- Edges (cheap, no LLM calls: just read decisions from state) ----------

    def decide_to_generate(state):
        return "generate" if state["documents"] else next_fallback(state)

    # ---------- Wiring ----------

    g = StateGraph(GraphState)
    for name, fn in [("route", route), ("retrieve", retrieve), ("grade_documents", grade_documents),
                     ("rewrite", rewrite), ("web_search", web_search_node), ("generate", generate),
                     ("check", check), ("give_up", give_up)]:
        g.add_node(name, fn)

    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda s: s["route"],
        {"vectorstore": "retrieve", "web_search": "web_search", "give_up": "give_up"})
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges("grade_documents", decide_to_generate,
        {"generate": "generate", "rewrite": "rewrite", "web_search": "web_search", "give_up": "give_up"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("web_search", "generate")
    g.add_edge("generate", "check")
    g.add_conditional_edges("check", lambda s: s["verdict"],
        {"done": END, "rewrite": "rewrite", "web_search": "web_search", "give_up": "give_up"})
    g.add_edge("give_up", END)
    return g.compile()


def ask(question: str, app=None) -> dict:
    """Run one question through the graph. Returns the final state."""
    app = app or build_graph()
    return app.invoke({"question": question, "web_searched": False, "rewrites": 0, "steps": []})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ask the self-correcting RAG system a question.")
    parser.add_argument("question")
    parser.add_argument("--scoped", action="store_true", help="knowledge base only, no web search")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="  %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # hide per-request HTTP logs

    app = build_graph(allow_web_fallback=False) if args.scoped else build_graph()
    result = ask(args.question, app)
    print(f"\nSOURCE: {result['answer_source']}\nANSWER: {result['generation']}")
