"""One place that decides which embedding model is used, for both indexing and querying."""
from src import config


def embedding_id() -> str:
    """Identifies the embedding model; stored with the index so a mismatch is caught at startup."""
    return f"{config.EMBED_PROVIDER}:{config.EMBED_MODEL}"


def make_embeddings():
    if config.EMBED_PROVIDER == "fastembed":
        from langchain_community.embeddings import FastEmbedEmbeddings
        return FastEmbedEmbeddings(model_name=config.EMBED_MODEL, cache_dir=config.EMBED_CACHE_DIR)
    if config.EMBED_PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=config.EMBED_MODEL, base_url=config.OLLAMA_BASE_URL)
    raise ValueError(f"Unknown EMBED_PROVIDER: {config.EMBED_PROVIDER!r}")
