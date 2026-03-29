"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from `.env` and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/ideavault.db"
    telegram_bot_token: str = ""
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    #: If non-empty, selected POST routes require header ``X-API-Key`` with the same value.
    api_key: str = ""
    #: Logical ``user_id`` for ``sessions`` row used by the web UI project picker.
    web_ui_user_id: str = "web-ui"
    #: TEMP diagnostics: ``RAG_RETRIEVAL_DEBUG=true`` — логировать цепочку Web UI → FTS RAG (см. ``RAG_E2E_DEBUG`` в логах).
    rag_retrieval_debug: bool = False

    # Optional OpenAI layer (retrieval unchanged; LLM only formats grounded context)
    llm_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 25.0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 200
    llm_debug_logging: bool = False

    # Telegram voice → OpenAI Speech-to-Text (Whisper-compatible endpoint)
    openai_stt_model: str = "whisper-1"
    stt_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for import-time use."""
    return Settings()


settings = get_settings()
