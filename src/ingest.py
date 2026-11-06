"""Build the vector index: load articles, chunk, embed, store in Chroma.

Run once (or whenever the source list changes):
    python -m src.ingest
"""
import logging

from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

log = logging.getLogger(__name__)

URLS = [
    # Anthropic engineering: agents, context, tools, MCP
    "https://www.anthropic.com/engineering/building-effective-agents",
    "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
    "https://www.anthropic.com/engineering/multi-agent-research-system",
    "https://www.anthropic.com/engineering/code-execution-with-mcp",
    "https://www.anthropic.com/engineering/writing-tools-for-agents",
    "https://www.anthropic.com/news/contextual-retrieval",
    # Lilian Weng: reasoning, reward hacking, hallucination
    "https://lilianweng.github.io/posts/2025-05-01-thinking/",
    "https://lilianweng.github.io/posts/2024-11-28-reward-hacking/",
    "https://lilianweng.github.io/posts/2024-07-07-hallucination/",
    # Evals
    "https://hamel.dev/blog/posts/evals-faq/",
    "https://hamel.dev/blog/posts/evals/",
    # Agents
    "https://huyenchip.com/2025/01/07/agents.html",
]

MIN_CHARS = 2000  # anything shorter is probably a blocked page or cookie wall


def load_documents(urls):
    docs = []
    for url in urls:
        try:
            loaded = WebBaseLoader(url).load()
        except Exception as e:  # one bad URL must not stop the whole build
            log.warning("FAILED %s -> %s: %s", url, type(e).__name__, e)
            continue
        chars = sum(len(d.page_content) for d in loaded)
        if chars < MIN_CHARS:
            log.warning("SKIPPED %s (only %d chars)", url, chars)
            continue
        log.info("%8d chars  %s", chars, url)
        docs.extend(loaded)
    return docs


def build_index(urls=URLS):
    docs = load_documents(urls)
    if not docs:
        raise RuntimeError("No documents loaded; refusing to wipe the existing index.")

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    log.info("Split %d documents into %d chunks", len(docs), len(chunks))

    store = Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=OllamaEmbeddings(model=config.EMBED_MODEL),
        persist_directory=config.CHROMA_DIR,
    )
    store.reset_collection()  # rebuild from scratch: re-running never duplicates

    step = config.EMBED_BATCH_SIZE
    for i in range(0, len(chunks), step):  # batches: one huge request crashed Ollama
        store.add_documents(chunks[i : i + step])
        log.info("Indexed %d/%d", min(i + step, len(chunks)), len(chunks))

    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    n = build_index()
    print(f"Done: {n} chunks in {config.CHROMA_DIR}")
