from functools import lru_cache

import httpx
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    """Create a cached Ollama chat client."""
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        temperature=0.1,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    """Create a cached Ollama embedding client."""
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.EMBEDDING_MODEL,
    )


def check_ollama_status() -> dict:
    """Return availability and model presence for local Ollama."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - best effort health endpoint
        return {
            "available": False,
            "error": str(exc),
            "models": [],
            "llm_model_ready": False,
            "embedding_model_ready": False,
        }

    model_names = [item.get("name", "") for item in payload.get("models", [])]
    return {
        "available": True,
        "models": model_names,
        "llm_model_ready": any(name.startswith(f"{settings.LLM_MODEL}:") or name == settings.LLM_MODEL for name in model_names),
        "embedding_model_ready": any(
            name.startswith(f"{settings.EMBEDDING_MODEL}:") or name == settings.EMBEDDING_MODEL for name in model_names
        ),
    }
