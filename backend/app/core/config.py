from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── OpenAI ───────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Groq ─────────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_chat_model: str = "llama3-70b-8192"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://support:support@postgres:5432/supportdb"
    )
    sync_database_url: str = (
        "postgresql://support:support@postgres:5432/supportdb"
    )

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # ── LangSmith ────────────────────────────────────────────────────────────
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "ai-support-desk"

    # ── Agent / RAG ───────────────────────────────────────────────────────────
    confidence_threshold: float = 0.6
    max_ticket_retries: int = 3

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_tickets: str = "10/minute"

    @field_validator("openai_api_key")
    @classmethod
    def _warn_missing_key(cls, v: str) -> str:
        if not v:
            import warnings
            warnings.warn(
                "OPENAI_API_KEY is not set — agent calls will fail.",
                stacklevel=2,
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
