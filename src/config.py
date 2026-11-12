"""All settings in one place, read from environment variables (.env locally, real env vars in Docker)."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


# Models
# LLM_PROVIDER: "ollama" (local) or "groq" (cloud, free tier).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
# Main model: generator, query rewriter, hallucination + answer checks.
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("LOCAL_LLM", "qwen3:8b")
# Light model: router + retrieval grader (many short yes/no calls). Defaults to the main model.
# On Groq, a separate model also gets its own free-tier token quota.
GRADER_MODEL = os.getenv("GRADER_MODEL") or LLM_MODEL
# Groq gpt-oss models think before answering; thinking tokens count against rate limits.
GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "low")
# Embeddings: "ollama" (local dev, needs Ollama running) or "fastembed" (small ONNX model inside the
# process; used for deployment, where there is no Ollama). An index only works with the model that built it.
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "ollama")
EMBED_MODEL = os.getenv("EMBED_MODEL") or (
    "BAAI/bge-small-en-v1.5" if EMBED_PROVIDER == "fastembed" else "nomic-embed-text")
EMBED_CACHE_DIR = os.getenv("EMBED_CACHE_DIR") or None   # where fastembed keeps the downloaded model
# Where Ollama is reachable. None = the default (localhost:11434). In Docker: http://host.docker.internal:11434
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or None

# Vector store
CHROMA_DIR = os.getenv("CHROMA_DIR", str(PROJECT_ROOT / "chroma_db"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "rag-chroma")
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))

# Ingestion
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "250"))          # tokens
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "0"))
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "64"))

# Graph behaviour
ALLOW_WEB_FALLBACK = _bool("ALLOW_WEB_FALLBACK", True)
MAX_REWRITES = int(os.getenv("MAX_REWRITES", "1"))
WEB_MAX_RESULTS = int(os.getenv("WEB_MAX_RESULTS", "3"))
GRADER_CONCURRENCY = int(os.getenv("GRADER_CONCURRENCY", "4"))  # chunks graded in parallel

# Public demo protection: max questions per visitor (IP) per hour. 0 = no limit (local dev).
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "0"))

# Evals: a different model family from the pipeline's, so the judge isn't grading its own work
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "qwen/qwen3.8-27b")
