"""
Application settings, loaded from environment variables (or a .env file
in development). Nothing secret is hardcoded here — see .env.example for
what needs to be set.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Where the SQLite database file lives. Swap to a Postgres URL later
    # (e.g. "postgresql://user:pass@host/db") without changing any other code —
    # SQLAlchemy abstracts the difference.
    database_url: str = "sqlite:///./walkguide.db"

    # Secret used to sign JWT auth tokens. MUST be overridden in production —
    # generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret: str = "change-me-before-deploying"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 12  # 12 hours

    # Comma-separated list of origins allowed to call this API (your
    # frontend's dev + production URLs).
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
