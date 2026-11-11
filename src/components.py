"""Building blocks used by the graph: LLM, retriever, prompts, graders, router, rewriter, web search.

Every grader returns a Pydantic object, so callers read `.binary_score` / `.reasoning`.
"""
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field

from src import config
from src.embeddings import embedding_id, make_embeddings

# ---------- LLM + retriever ----------

def make_llm(model: str):
    """Build a chat model for the configured provider, with provider-specific settings."""
    if config.LLM_PROVIDER == "ollama":
        # reasoning=False turns off Qwen3's thinking mode
        return init_chat_model(model, model_provider="ollama", temperature=0, reasoning=False,
                               base_url=config.OLLAMA_BASE_URL)
    if config.LLM_PROVIDER == "groq":
        kwargs = {"max_retries": 6}  # free tier returns 429 when over the per-minute limit; back off and retry
        if model.startswith("openai/gpt-oss"):
            kwargs["reasoning_effort"] = config.GROQ_REASONING_EFFORT
        return init_chat_model(model, model_provider="groq", temperature=0, **kwargs)
    return init_chat_model(model, model_provider=config.LLM_PROVIDER, temperature=0)


llm = make_llm(config.LLM_MODEL)              # generator, rewriter, hallucination + answer checks
grader_llm = make_llm(config.GRADER_MODEL)    # router + retrieval grader

vectorstore = Chroma(
    collection_name=config.COLLECTION_NAME,
    embedding_function=make_embeddings(),
    persist_directory=config.CHROMA_DIR,
)
# Searching an index with a different embedding model than the one that built it returns
# nonsense without any error, so check it explicitly.
_built_with = (vectorstore._collection.metadata or {}).get("embedding")
if _built_with and _built_with != embedding_id():
    raise RuntimeError(
        f"The index in {config.CHROMA_DIR} was built with {_built_with}, but EMBED_PROVIDER/EMBED_MODEL "
        f"say {embedding_id()}. Rebuild it with `python -m src.ingest` or fix the settings.")
retriever = vectorstore.as_retriever(search_kwargs={"k": config.RETRIEVER_K})


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(
        f'<document index="{i}" source="{d.metadata.get("source", "unknown")}">\n'
        f"{d.page_content}\n</document>"
        for i, d in enumerate(docs, start=1)
    )


# ---------- Generator ----------

REFUSAL = (
    "Sorry, I couldn't find information about that in my knowledge base, "
    "so I'm not able to answer it reliably. Feel free to ask about AI agents, "
    "context engineering, LLM reasoning, or evaluation."
)

generate_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions using ONLY the documents provided by the user.\n\n"
     "Rules:\n"
     "1. Every statement in your answer must be supported by the documents. "
     "Do not use outside or prior knowledge, even if you are confident you know the answer.\n"
     "2. The documents come from an automatic search and may be irrelevant to the question. "
     "First decide whether they actually contain the answer.\n"
     f"3. If they do not, reply with exactly: \"{REFUSAL}\" and nothing else.\n"
     "4. If they do, answer in at most three sentences and cite the supporting "
     "document numbers in square brackets, like [1] or [2][3]."),
    ("human", "<documents>\n{context}\n</documents>\n\nQuestion: {question}"),
])


def normalize_citations(text: str) -> str:
    """Some models (e.g. gpt-oss) cite as 【1】; convert to [1] so parsing and the UI see one format."""
    return text.replace("【", "[").replace("】", "]").strip()


rag_chain = generate_prompt | llm | StrOutputParser() | RunnableLambda(normalize_citations)


# ---------- Retrieval grader ----------

class GradeDocument(BaseModel):
    """Relevance check for a retrieved document."""
    reasoning: str = Field(description="One or two sentences on how the document relates to the question")
    binary_score: Literal["yes", "no"] = Field(
        description="'yes' if the document is relevant to the question, otherwise 'no'"
    )


grade_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a grader assessing whether a retrieved document is relevant to a user question.\n"
     "Grade 'yes' if the document is about the same topic as the question or contains information "
     "that would help answer it, even partially. The document does NOT need to fully answer the question.\n"
     "Grade 'no' only if the document is about a different topic."),
    ("human", "Retrieved document:\n\n{document}\n\nUser question: {question}"),
])
retrieval_grader = (grade_prompt | grader_llm.with_structured_output(GradeDocument, method="json_schema")).with_retry(stop_after_attempt=3)


# ---------- Hallucination grader ----------

class GradeHallucination(BaseModel):
    """Whether the answer is supported by the documents."""
    reasoning: str = Field(
        description="Briefly check the answer's main claims against the documents. "
                    "Quote any claim that adds facts not found in the documents, or say all claims are supported."
    )
    binary_score: Literal["yes", "no"] = Field(
        description="'yes' if every factual claim in the answer is supported by the documents, otherwise 'no'"
    )


hallucination_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a grader checking whether an answer is grounded in a set of documents.\n\n"
     "How to judge:\n"
     "1. Check the meaning of each factual claim in the answer against the documents.\n"
     "2. Paraphrases, summaries, and combinations of information from several documents "
     "count as SUPPORTED, as long as the documents say it.\n"
     "3. Ignore citation numbers like [1] or [2]. Judge only whether the content is in the documents.\n"
     "4. Answer 'no' only if the answer adds a fact, name, number, or detail that is NOT in the documents, "
     "even if that fact is true in the real world."),
    ("human", "<documents>\n{documents}\n</documents>\n\nAnswer to check:\n{generation}"),
])
hallucination_grader = (hallucination_prompt | llm.with_structured_output(GradeHallucination, method="json_schema")).with_retry(stop_after_attempt=3)


# ---------- Answer grader ----------

class GradeAnswer(BaseModel):
    """Whether the answer resolves the question."""
    binary_score: Literal["yes", "no"] = Field(
        description="'yes' if the answer resolves the question, otherwise 'no'"
    )


answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a grader checking whether an answer resolves a user's question. "
     "Answer 'yes' if it directly addresses and answers the question. "
     "Answer 'no' if it is off-topic, only partially relevant, or declines to answer."),
    ("human", "Question: {question}\n\nAnswer:\n{generation}"),
])
answer_grader = (answer_prompt | llm.with_structured_output(GradeAnswer, method="json_schema")).with_retry(stop_after_attempt=3)


# ---------- Router (not used by the graph since evals showed it hurt; kept for the notebook/experiments) ----------

class RouteQuery(BaseModel):
    """Where to send the user's question."""
    datasource: Literal["vectorstore", "web_search"] = Field(
        description="'vectorstore' for questions about the knowledge base topics, otherwise 'web_search'"
    )


router_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You route a user question to either a vectorstore or web search.\n\n"
     "The vectorstore contains articles on: AI agents and agent design patterns, "
     "context engineering, multi-agent systems, tool design for agents and MCP, "
     "RAG and contextual retrieval, LLM reasoning and test-time compute, "
     "reward hacking, hallucinations in LLMs, and LLM evaluation (evals).\n"
     "The articles come from: Anthropic's engineering blog (building effective agents, "
     "context engineering, the multi-agent research system, code execution with MCP, "
     "writing tools for agents, contextual retrieval), Lilian Weng's blog, Hamel Husain's blog, "
     "and Chip Huyen's blog. Questions about what these authors or articles say belong in the vectorstore.\n\n"
     "Rules:\n"
     "1. Use 'vectorstore' for questions related to these topics. "
     "Be lenient: the question does not need to use the exact keywords.\n"
     "2. Use 'web_search' for anything else, and for questions about recent news, "
     "current events, or the latest releases, even if the topic matches, "
     "because the vectorstore is a fixed snapshot."),
    ("human", "{question}"),
])
question_router = (router_prompt | grader_llm.with_structured_output(RouteQuery, method="json_schema")).with_retry(stop_after_attempt=3)


# ---------- Query rewriter ----------

rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You rewrite a user question into a better search query for a vector database of "
     "articles about AI agents, context engineering, multi-agent systems, tools and MCP, "
     "RAG, LLM reasoning, reward hacking, hallucinations, and LLM evaluation.\n"
     "Keep the original meaning. Replace vague or casual words with the specific technical terms "
     "the articles would use, but do NOT add topics, concepts or keywords the user did not ask about. "
     "Keep it short: one search query of at most 15 words.\n"
     "Do not answer the question. Output only the rewritten query, nothing else."),
    ("human", "{question}"),
])
query_rewriter = rewrite_prompt | llm | StrOutputParser()


# ---------- Web search ----------

_web_search_tool = TavilySearch(max_results=config.WEB_MAX_RESULTS, topic="general")


def web_search(query: str) -> list[Document]:
    """Search the web and return results as Documents, same shape as the retriever."""
    response = _web_search_tool.invoke({"query": query})
    return [
        Document(page_content=r["content"], metadata={"source": r["url"], "title": r.get("title", "")})
        for r in response["results"]
    ]
