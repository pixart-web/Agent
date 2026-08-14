from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent API"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://agent:agent@localhost:5432/agent"
    redis_url: str = "redis://localhost:6379/0"
    service_connect_timeout_seconds: int = 2
    auth_secret_key: str = Field(min_length=32)
    auth_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=30, gt=0)
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_domain: str | None = None
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_requests: int = Field(default=10, gt=0)
    auth_rate_limit_window_seconds: int = Field(default=60, gt=0)
    auth_rate_limit_fail_open: bool = True
    auth_cleanup_retention_days: int = Field(default=7, ge=0)
    ai_provider: Literal["openai", "fake"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = Field(default="gpt-5.4-mini", min_length=1)
    ai_request_timeout_seconds: float = Field(default=60, gt=0)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    supervisor_max_tasks: int = Field(default=20, ge=1, le=100)
    supervisor_max_command_chars: int = Field(default=10_000, ge=100, le=100_000)
    supervisor_max_feedback_chars: int = Field(default=5_000, ge=100, le=50_000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("auth_cookie_domain", "openai_api_key", mode="before")
    @classmethod
    def empty_optional_string_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("openai_model")
    @classmethod
    def require_non_empty_model(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("OPENAI_MODEL must not be empty")
        return normalized

    @property
    def web_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.web_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.web_origin_list:
            raise ValueError("WEB_ORIGINS must contain at least one origin")
        if "*" in self.web_origin_list:
            raise ValueError("WEB_ORIGINS cannot contain a wildcard with credentials")
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError("SameSite=None requires AUTH_COOKIE_SECURE=true")
        if self.app_env.lower() == "production":
            insecure_markers = ("development", "example", "change-me", "replace")
            if any(marker in self.auth_secret_key.lower() for marker in insecure_markers):
                raise ValueError("Production requires a non-example authentication secret")
            if not self.auth_cookie_secure:
                raise ValueError("Production requires AUTH_COOKIE_SECURE=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
