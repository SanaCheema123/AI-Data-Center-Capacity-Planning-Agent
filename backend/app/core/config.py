from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Data Center Capacity Planning Agent"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"

    database_url: str = "sqlite:///./capacity_dev.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = Field(default="development-only-change-me-32-byte-secret-key", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    ai_provider: str = "local"
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    forecast_default_model: str = "prophet"
    report_output_dir: str = "./artifacts/reports"
    collector_sync_minutes: int = Field(default=15, ge=1, le=1440)
    bootstrap_first_user_as_admin: bool = True
    allow_public_registration: bool = True

    @model_validator(mode="after")
    def validate_production(self):
        if self.app_env.lower() == "production":
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
            if self.jwt_secret.startswith("development-only") or self.jwt_secret.startswith("change-me") or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be a strong, non-default secret in production")
            # Never allow an internet-facing production process to bootstrap an
            # administrator through public registration. Production admins are
            # created explicitly with app.bootstrap_admin.
            self.bootstrap_first_user_as_admin = False
            self.allow_public_registration = False
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL; SQLite is development-only")
            origins = [x.strip() for x in self.frontend_origin.split(",") if x.strip()]
            if not origins or "*" in origins:
                raise ValueError("FRONTEND_ORIGIN must list explicit trusted origins in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
