"""Naive RAG baseline: retrieve once, generate once, no checks, no recovery.

Same retriever, same prompt and same model as the graph, so any difference in the
evals comes from the self-correction alone.
"""
from src.components import REFUSAL, format_docs, rag_chain, retriever


def naive_ask(question: str) -> dict:
    docs = retriever.invoke(question)
    generation = rag_chain.invoke({"context": format_docs(docs), "question": question})
    refused = generation.strip() == REFUSAL
    return {
        "generation": generation,
        "documents": docs,
        "answer_source": "none" if refused else "knowledge_base",
        "steps": [{"step": "retrieve", "query": question, "found": len(docs)},
                  {"step": "generate", "from_source": "knowledge_base", "refused": refused}],
    }
