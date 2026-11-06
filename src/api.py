"""HTTP API for the self-correcting RAG system.

Run (from the project root, venv active, Ollama running):
    uvicorn src.api:app --reload --port 8000
Then open http://localhost:8000/docs to try it in the browser.
"""
import logging
import re
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.components import REFUSAL
from src.graph import ask, build_graph

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("api")

app = FastAPI(title="Self-Correcting RAG API", version="0.1.0")

# Compile both graphs once at startup, not per request.
GRAPHS = {"research": build_graph(allow_web_fallback=True),
          "scoped": build_graph(allow_web_fallback=False)}


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    mode: Literal["research", "scoped"] = "research"


class Source(BaseModel):
    index: int               # the number the answer cites, e.g. [2]
    url: str
    title: str = ""
    snippet: str


class AskResponse(BaseModel):
    answer: str
    answer_source: Literal["knowledge_base", "web", "none"]
    refused: bool
    mode: str
    sources: list[Source]    # the documents the final answer was generated from
    cited: list[int]         # which of those the answer actually cites
    steps: list[dict]        # how the answer was produced
    latency_s: float


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    # A plain `def` (not async): the graph makes blocking calls, so FastAPI runs this in a
    # worker thread instead of freezing the server for other requests.
    start = time.perf_counter()
    try:
        result = ask(req.question, GRAPHS[req.mode])
    except Exception:
        log.exception("Graph failed for question: %r", req.question)
        raise HTTPException(status_code=502, detail="The RAG pipeline failed. Is Ollama running?")

    answer = result["generation"]
    refused = answer.strip() == REFUSAL
    docs = [] if refused else result.get("documents", [])

    sources = [
        Source(index=i, url=d.metadata.get("source", "unknown"),
               title=d.metadata.get("title", ""), snippet=d.page_content[:300])
        for i, d in enumerate(docs, start=1)
    ]
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(docs)})

    return AskResponse(
        answer=answer, answer_source=result["answer_source"], refused=refused, mode=req.mode,
        sources=sources, cited=cited, steps=result.get("steps", []),
        latency_s=round(time.perf_counter() - start, 2),
    )
