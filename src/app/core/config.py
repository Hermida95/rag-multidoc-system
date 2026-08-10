from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "rag-multidoc-system"
    app_env: str = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 5

    # Redis / Celery
    celery_broker_url: str
    celery_result_backend: str

    # AI Provider
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2

    # Chunking
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 75

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_min_similarity: float = 0.5

    # Storage
    upload_dir: str = "/app/storage/uploads"
    max_upload_size_mb: int = 25

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
