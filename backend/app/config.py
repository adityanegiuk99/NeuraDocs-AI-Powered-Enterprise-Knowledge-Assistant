"""
AI-Powered Internal Knowledge Assistant
Application configuration via pydantic-settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "knowledge-assistant"
    app_env: str = "development"
    debug: bool = True

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/knowledge_assistant.db"

    # --- Auth ---
    jwt_secret_key: str = "change-me-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # --- Embeddings ---
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_provider: str = "huggingface"  # huggingface | openai
    embedding_dimension: int = 384

    # --- LLM ---
    llm_provider: str = "openai"  # openai | groq | local
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    groq_api_key: str = ""
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.1

    # --- Retrieval ---
    faiss_index_path: str = "data/faiss_index/index.faiss"
    faiss_metadata_path: str = "data/faiss_index/metadata.json"
    top_k_retrieval: int = 50
    top_k_rerank: int = 5
    similarity_threshold: float = 0.35

    # --- Paths ---
    upload_dir: str = "data/uploads"
    benchmark_dir: str = "data/benchmarks"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def ensure_directories(self):
        """Create required data directories if they don't exist."""
        for dir_path in [self.upload_dir, "data/faiss_index", self.benchmark_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
