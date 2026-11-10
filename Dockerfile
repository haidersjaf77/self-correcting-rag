# Image for the self-correcting RAG API.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is cached and only rebuilt when requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Then the code (changes often, rebuilds fast).
COPY src/ src/

# Don't run as root. /data holds the Chroma index (mounted as a volume, not baked into the image).
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app:app /data
USER app
ENV CHROMA_DIR=/data/chroma_db

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
