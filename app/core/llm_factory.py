from langchain_ollama import OllamaLLM, OllamaEmbeddings
from app.core.config import settings

def get_llm():
    """Initialize and return the Ollama LLM."""
    return OllamaLLM(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.LLM_MODEL
    )

def get_embeddings():
    """Initialize and return the Ollama Embeddings."""
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.EMBEDDING_MODEL
    )
