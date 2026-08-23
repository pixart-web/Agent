from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CodexSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CodexTaskRequest(CodexSchema):
    run_id: UUID
    mode: Literal["implement", "review", "fix"]
    repository: str
    base_branch: str
    working_branch: str | None = None
    title: str
    instructions: str
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=30)
    allowed_paths: list[str] = Field(default_factory=list, max_length=100)
    pull_request_number: int | None = Field(default=None, ge=1)


class CodexReviewFinding(CodexSchema):
    severity: Literal["low", "medium", "high", "critical"]
    file: str = Field(min_length=1, max_length=1000)
    line: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=5000)
    suggestion: str = Field(min_length=1, max_length=5000)


class CodexTaskResult(CodexSchema):
    summary: str = Field(min_length=1, max_length=20_000)
    base_branch: str | None = None
    files_changed: list[str] = Field(default_factory=list, max_length=1000)
    tests_run: list[str] = Field(default_factory=list, max_length=200)
    tests_passed: bool | None = None
    commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    branch: str | None = None
    pull_request_number: int | None = None
    pull_request_url: str | None = None
    findings: list[CodexReviewFinding] = Field(default_factory=list, max_length=200)
    risk: Literal["low", "medium", "high", "critical"] | None = None
    recommended_action: str | None = Field(default=None, max_length=5000)
    exit_code: int | None = None
    model: str | None = Field(default=None, max_length=128)


class CodexAdapterChangeResult(CodexSchema):
    summary: str = Field(min_length=1, max_length=20_000)


class CodexAdapterReviewResult(CodexSchema):
    summary: str = Field(min_length=1, max_length=20_000)
    findings: list[CodexReviewFinding] = Field(default_factory=list, max_length=200)
    risk: Literal["low", "medium", "high", "critical"]
    recommended_action: str = Field(min_length=1, max_length=5000)


class CodexRepositoryInput(CodexSchema):
    repository: str = Field(min_length=3, max_length=200)


class CodexImplementTaskInput(CodexRepositoryInput):
    base_branch: str = Field(default="main", min_length=1, max_length=200)
    working_branch: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=256)
    instructions: str = Field(min_length=1, max_length=50_000)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=30)
    allowed_paths: list[str] = Field(default_factory=list, max_length=100)


class CodexReviewPullRequestInput(CodexRepositoryInput):
    pull_request_number: int = Field(ge=1)
    review_focus: str = Field(default="Correctness, security, and regressions", max_length=20_000)


class CodexFixPullRequestInput(CodexRepositoryInput):
    pull_request_number: int = Field(ge=1)
    instructions: str = Field(min_length=1, max_length=50_000)
    allowed_paths: list[str] = Field(default_factory=list, max_length=100)


class CodexImplementationOutput(CodexSchema):
    codex_run_id: UUID
    summary: str
    files_changed: list[str]
    tests_run: list[str]
    tests_passed: bool
    commit_sha: str
    branch: str
    base_branch: str
    pull_request_number: int | None = None
    pull_request_url: str | None = None
    exit_code: int | None = None
    model: str | None = None


class CodexReviewOutput(CodexSchema):
    codex_run_id: UUID
    summary: str
    findings: list[CodexReviewFinding]
    risk: Literal["low", "medium", "high", "critical"]
    recommended_action: str
    exit_code: int | None = None
    model: str | None = None
    base_branch: str
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"
