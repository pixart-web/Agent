from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.workflow_enums import CodexRunStatus


class CodexRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    task_action_id: UUID
    repository: str
    base_branch: str
    working_branch: str | None
    status: CodexRunStatus
    instruction: str
    acceptance_criteria: list[str]
    runner_type: str
    model: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    exit_code: int | None
    summary: str | None
    error_code: str | None
    error_message: str | None
    files_changed: list[str]
    tests_run: list[str]
    tests_passed: bool | None
    commit_sha: str | None
    pull_request_number: int | None
    pull_request_url: str | None
    correlation_id: UUID
    created_at: datetime
    updated_at: datetime


class CodexIntegrationStatus(BaseModel):
    enabled: bool
    runner: str
    allowed_repositories: list[str]
    credential_configured: bool
    github_credential_configured: bool
    timeout_seconds: int
