from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Kiko API"
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
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str | None = None
    execution_default_timeout_seconds: int = Field(default=60, gt=0)
    execution_max_retries: int = Field(default=3, ge=0, le=10)
    execution_stale_after_seconds: int = Field(default=900, ge=30)
    outbox_poll_interval_seconds: float = Field(default=2, gt=0)
    outbox_batch_size: int = Field(default=50, ge=1, le=500)
    outbox_max_attempts: int = Field(default=10, ge=1, le=100)

    agent_max_context_chars: int = Field(default=20_000, ge=1_000, le=100_000)
    agent_max_actions_per_task: int = Field(default=10, ge=1, le=50)
    agent_max_feedback_chars: int = Field(default=5_000, ge=100, le=50_000)
    github_integration_enabled: bool = False
    github_token: SecretStr | None = None
    github_allowed_repositories: str = "pixart-web/Agent"
    github_api_timeout_seconds: float = Field(default=30, gt=0, le=120)
    github_protected_branches: str = "main"
    github_allowed_branch_prefixes: str = "feature/,fix/,chore/,docs/"
    github_max_file_bytes: int = Field(default=500_000, ge=1_000, le=5_000_000)
    github_max_output_chars: int = Field(default=100_000, ge=1_000, le=1_000_000)
    codex_integration_enabled: bool = False
    codex_runner: Literal["cli"] = "cli"
    codex_credential_configured: bool = False
    codex_binary: str = Field(default="codex", min_length=1, max_length=500)
    codex_api_key: SecretStr | None = None
    codex_model: str | None = Field(default=None, max_length=128)
    codex_timeout_seconds: int = Field(default=1800, ge=60, le=7200)
    codex_max_output_chars: int = Field(default=200_000, ge=1_000, le=1_000_000)
    codex_workspace_root: str = Field(default="/tmp/kiko-codex", min_length=1, max_length=1000)
    codex_allowed_repositories: str = "pixart-web/Agent"
    codex_max_changed_files: int = Field(default=100, ge=1, le=1000)
    codex_max_diff_bytes: int = Field(default=2_000_000, ge=10_000, le=20_000_000)
    codex_retain_workspaces: bool = False
    email_integration_enabled: bool = False
    email_provider: Literal["gmail"] = "gmail"
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None
    email_allowed_accounts: str = ""
    email_internal_domains: str = ""
    email_max_body_chars: int = Field(default=50_000, ge=1_000, le=1_000_000)
    email_max_attachment_bytes: int = Field(default=10_000_000, ge=0)
    email_send_enabled: bool = False
    email_mark_read_enabled: bool = False
    integration_encryption_key: SecretStr | None = None
    email_max_recipients: int = Field(default=10, ge=1, le=100)
    email_max_search_results: int = Field(default=100, ge=1, le=500)
    email_api_timeout_seconds: float = Field(default=30, gt=0, le=120)
    email_oauth_state_expire_minutes: int = Field(default=10, ge=1, le=60)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "auth_cookie_domain",
        "openai_api_key",
        "github_token",
        "codex_api_key",
        "codex_model",
        "google_client_id",
        "google_client_secret",
        "google_redirect_uri",
        "integration_encryption_key",
        mode="before",
    )
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

    @property
    def github_allowed_repository_list(self) -> list[str]:
        return [
            item.strip() for item in self.github_allowed_repositories.split(",") if item.strip()
        ]

    @property
    def github_protected_branch_list(self) -> list[str]:
        return [item.strip() for item in self.github_protected_branches.split(",") if item.strip()]

    @property
    def github_allowed_branch_prefix_list(self) -> list[str]:
        return [
            item.strip() for item in self.github_allowed_branch_prefixes.split(",") if item.strip()
        ]

    @property
    def codex_allowed_repository_list(self) -> list[str]:
        return [item.strip() for item in self.codex_allowed_repositories.split(",") if item.strip()]

    @property
    def email_allowed_account_list(self) -> list[str]:
        return [
            item.strip().lower() for item in self.email_allowed_accounts.split(",") if item.strip()
        ]

    @property
    def email_internal_domain_list(self) -> list[str]:
        return [
            item.strip().lower() for item in self.email_internal_domains.split(",") if item.strip()
        ]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.web_origin_list:
            raise ValueError("WEB_ORIGINS must contain at least one origin")
        if "*" in self.web_origin_list:
            raise ValueError("WEB_ORIGINS cannot contain a wildcard with credentials")
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError("SameSite=None requires AUTH_COOKIE_SECURE=true")
        if self.github_integration_enabled and not self.github_allowed_repository_list:
            raise ValueError("GitHub integration requires at least one allowed repository")
        if self.codex_integration_enabled and not self.codex_allowed_repository_list:
            raise ValueError("Codex integration requires at least one allowed repository")
        if self.email_integration_enabled:
            required = (
                self.google_client_id,
                self.google_client_secret,
                self.google_redirect_uri,
                self.integration_encryption_key,
            )
            if not all(required):
                raise ValueError("Email integration requires Google OAuth and encryption settings")
            if not self.email_allowed_account_list:
                raise ValueError("Email integration requires at least one allowed account")
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
