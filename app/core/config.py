import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "PrivAI - Secure Enterprise AI Assistant"
    API_PREFIX: str = "/api/v1"
    APP_ENV: str = "development"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    LLM_TIMEOUT_SECONDS: int = 120

    DOCS_DIR: str = os.path.join(os.getcwd(), "data", "docs")
    CHROMA_DIR: str = os.path.join(os.getcwd(), "data", "chroma")
    COLLECTION_NAME: str = "enterprise_docs"

    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 150
    RETRIEVAL_TOP_K: int = 4
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = 3
    RERANK_MIN_SCORE: float = 0.15
    RETRIEVAL_MIN_SOURCE_LENGTH: int = 50
    RETRIEVAL_RETRY_LIMIT: int = 1
    VALIDATION_RETRY_LIMIT: int = 1
    LLM_RETRY_COUNT: int = 2
    LLM_RETRY_BACKOFF_SECONDS: float = 0.6

    ALLOWED_FILE_EXTENSIONS: str = ".txt,.pdf"
    MAX_UPLOAD_FILES: int = 20
    MAX_QUERY_LENGTH: int = 4000

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = os.path.join(os.getcwd(), "logs", "app.log")
    QUERY_CACHE_TTL_SECONDS: int = 180
    QUERY_CACHE_MAX_ENTRIES: int = 256
    EVALUATION_DATASET_PATH: str = os.path.join(os.getcwd(), "data", "eval", "sample_eval.jsonl")
    EVALUATION_REPORT_DIR: str = os.path.join(os.getcwd(), "reports", "evaluation")

    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    def allowed_extensions(self) -> set[str]:
        return {ext.strip().lower() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",") if ext.strip()}


settings = Settings()
