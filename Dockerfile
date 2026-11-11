# Image for the self-correcting RAG API.
# The index is built INTO the image at build time with a small local embedding model (fastembed),
# so the container needs no Ollama and no embedding API: just a GROQ_API_KEY (and TAVILY_API_KEY).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EMBED_PROVIDER=fastembed \
    EMBED_MODEL=BAAI/bge-small-en-v1.5 \
    EMBED_CACHE_DIR=/app/models \
    CHROMA_DIR=/app/index

WORKDIR /app
RUN useradd --create-home --uid 1000 app && chown app:app /app
USER app
ENV PATH="/home/app/.local/bin:$PATH"

# 1) Dependencies (cached until requirements.txt changes).
COPY --chown=app:app requirements.txt .
RUN pip install --user -r requirements.txt

# 2) The index: download the embedding model, scrape the articles, embed, store in /app/index.
#    Only the files ingest needs are copied first, so editing other code doesn't trigger a re-index.
COPY --chown=app:app src/__init__.py src/config.py src/embeddings.py src/ingest.py src/
RUN python -m src.ingest

# 3) The rest of the code (changes often, rebuilds in seconds).
COPY --chown=app:app src/ src/

# Hosting platforms (e.g. Render) tell the app which port to use via $PORT.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=3)" || exit 1
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
