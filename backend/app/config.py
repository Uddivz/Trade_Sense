"""
TradeSense — Application Configuration
Loads all settings from environment variables with type validation.
Uses Pydantic BaseSettings for strict, self-documenting configuration.
"""
from functools import lru_cache
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict
# pyrefly: ignore [missing-import]
from pydantic import field_validator


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────
    app_name: str = "TradeSense API"
    app_version: str = "1.0.0"
    environment: str = "development"  # development | staging | production
    debug: bool = False

    # ── Database ───────────────────────────────────────────────────────
    database_url: str  # postgresql+asyncpg://user:pass@host:port/dbname

    # ── Security ───────────────────────────────────────────────────────
    secret_key: str  # min 32 chars; generate with: openssl rand -hex 32
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # ── CORS ───────────────────────────────────────────────────────────
    allowed_origins: str | list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    # ── File Upload ────────────────────────────────────────────────────
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB

    # ── Market Data ────────────────────────────────────────────────────
    market_data_cache_ttl_seconds: int = 3600  # 1 hour

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("secret_key")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance — reads .env once per process lifetime."""
    return Settings()


# Convenience alias used across the application
settings = get_settings()
