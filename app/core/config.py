from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "PrivAI – Secure Enterprise AI Assistant"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3" # or "mistral"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    DOCS_DIR: str = os.path.join(os.getcwd(), "data", "docs")
    CHROMA_DIR: str = os.path.join(os.getcwd(), "data", "chroma")
    
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    COLLECTION_NAME: str = "enterprise_docs"

settings = Settings()
