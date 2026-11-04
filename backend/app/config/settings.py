from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Looks for .env in backend/ first, then the repo root.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES = (_BACKEND_DIR.parent / ".env", _BACKEND_DIR / ".env")


def _to_psycopg(url: str) -> str:
    """Neon gives postgresql://… ; SQLAlchemy needs the psycopg (v3) driver prefix."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    # App
    environment: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "AdaptiveLearn AI API"
    frontend_url: str = "http://localhost:3000"  # used to build links in emails
    api_v1_prefix: str = "/api/v1"
    trust_proxy_headers: bool = False  # true only behind our own reverse proxy
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Database — pooled URL for the app, direct URL for Alembic migrations
    database_url: str
    database_direct_url: str | None = None

    # Redis / Celery
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # Auth
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    refresh_cookie_name: str = "al_refresh"
    # Off for now: new students are active straight away. Set REQUIRE_EMAIL_VERIFICATION=true
    # to require clicking an emailed link before the first sign-in.
    require_email_verification: bool = False
    email_token_hours: int = 24
    reset_token_minutes: int = 30
    policy_version: str = "2026-11-01"  # bump when terms/privacy change; recorded with consent

    # Email — "console" logs messages (dev); "smtp" sends them
    email_backend: Literal["console", "smtp"] = "console"
    email_from: str = "AdaptiveLearn AI <no-reply@adaptivelearn.local>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True

    # Process outbox events in the API process right after commit, so mastery, revision and
    # the error notebook update even when no Celery worker is running (local development).
    # Set false in production and run the workers; the outbox + idempotency make both safe.
    process_events_inline: bool = True

    # Rate limits ("count/seconds")
    rate_limit_login: str = "10/60"
    rate_limit_register: str = "5/60"
    rate_limit_email: str = "5/300"

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_api_token: str = ""
    r2_public_url: str = ""

    # AI (provider-agnostic; see app/integrations/llm.py)
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_model: str = ""

    @field_validator("database_url", "database_direct_url")
    @classmethod
    def _driver(cls, v: str | None) -> str | None:
        return _to_psycopg(v) if v else v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment in ("staging", "production")

    @property
    def migration_url(self) -> str:
        return self.database_direct_url or self.database_url

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def r2_configured(self) -> bool:
        return all(
            v and not v.startswith("PASTE_")
            for v in (
                self.r2_account_id,
                self.r2_access_key_id,
                self.r2_secret_access_key,
                self.r2_bucket_name,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
