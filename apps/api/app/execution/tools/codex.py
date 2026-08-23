from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.execution.context import ExecutionContext
from app.execution.registry import ToolDefinition
from app.integrations.codex.base import CodexRunner
from app.integrations.codex.errors import CodexValidationError
from app.integrations.codex.runner import IsolatedCodexRunner
from app.integrations.codex.schemas import (
    CodexFixPullRequestInput,
    CodexImplementationOutput,
    CodexImplementTaskInput,
    CodexReviewOutput,
    CodexReviewPullRequestInput,
    CodexTaskRequest,
)
from app.models.workflow_enums import RiskLevel


class CodexImplementTaskHandler:
    def __init__(self, runner: CodexRunner) -> None:
        self.runner = runner

    def execute(
        self,
        context: ExecutionContext,
        payload: CodexImplementTaskInput,
    ) -> BaseModel:
        run_id = _run_id(context)
        result = self.runner.run_task(
            CodexTaskRequest(
                run_id=run_id,
                mode="implement",
                repository=payload.repository,
                base_branch=payload.base_branch,
                working_branch=payload.working_branch,
                title=payload.title,
                instructions=payload.instructions,
                acceptance_criteria=payload.acceptance_criteria,
                allowed_paths=payload.allowed_paths,
            ),
            context,
        )
        if not result.commit_sha or not result.branch or result.tests_passed is not True:
            raise CodexValidationError("Codex implementation result is incomplete")
        return CodexImplementationOutput(
            codex_run_id=run_id,
            summary=result.summary,
            files_changed=result.files_changed,
            tests_run=result.tests_run,
            tests_passed=True,
            commit_sha=result.commit_sha,
            branch=result.branch,
            base_branch=result.base_branch or payload.base_branch,
            exit_code=result.exit_code,
            model=result.model,
        )


class CodexReviewPullRequestHandler:
    def __init__(self, runner: CodexRunner) -> None:
        self.runner = runner

    def execute(
        self,
        context: ExecutionContext,
        payload: CodexReviewPullRequestInput,
    ) -> BaseModel:
        run_id = _run_id(context)
        result = self.runner.run_task(
            CodexTaskRequest(
                run_id=run_id,
                mode="review",
                repository=payload.repository,
                base_branch="pull-request",
                title=f"Review pull request #{payload.pull_request_number}",
                instructions=payload.review_focus,
                pull_request_number=payload.pull_request_number,
            ),
            context,
        )
        if result.risk is None or result.recommended_action is None:
            raise CodexValidationError("Codex review result is incomplete")
        return CodexReviewOutput(
            codex_run_id=run_id,
            summary=result.summary,
            findings=result.findings,
            risk=result.risk,
            recommended_action=result.recommended_action,
            base_branch=result.base_branch or "pull-request",
            exit_code=result.exit_code,
            model=result.model,
        )


class CodexFixPullRequestHandler:
    def __init__(self, runner: CodexRunner) -> None:
        self.runner = runner

    def execute(
        self,
        context: ExecutionContext,
        payload: CodexFixPullRequestInput,
    ) -> BaseModel:
        run_id = _run_id(context)
        result = self.runner.run_task(
            CodexTaskRequest(
                run_id=run_id,
                mode="fix",
                repository=payload.repository,
                base_branch="pull-request",
                title=f"Fix pull request #{payload.pull_request_number}",
                instructions=payload.instructions,
                acceptance_criteria=["The requested pull request fixes are complete"],
                allowed_paths=payload.allowed_paths,
                pull_request_number=payload.pull_request_number,
            ),
            context,
        )
        if not result.commit_sha or not result.branch or result.tests_passed is not True:
            raise CodexValidationError("Codex fix result is incomplete")
        return CodexImplementationOutput(
            codex_run_id=run_id,
            summary=result.summary,
            files_changed=result.files_changed,
            tests_run=result.tests_run,
            tests_passed=True,
            commit_sha=result.commit_sha,
            branch=result.branch,
            base_branch=result.base_branch or "pull-request",
            pull_request_number=payload.pull_request_number,
            exit_code=result.exit_code,
            model=result.model,
        )


def codex_tool_definitions(
    *,
    settings: Settings | None = None,
    runner: CodexRunner | None = None,
) -> list[ToolDefinition]:
    settings = settings or get_settings()
    runner = runner or IsolatedCodexRunner(settings=settings)
    return [
        ToolDefinition(
            name="codex.implement_task",
            version="1",
            description="Implement an approved task in an isolated repository workspace.",
            agent_types=frozenset({"development"}),
            risk_level=RiskLevel.YELLOW,
            timeout_seconds=settings.codex_timeout_seconds,
            max_retries=0,
            requires_approval=True,
            input_schema=CodexImplementTaskInput,
            output_schema=CodexImplementationOutput,
            handler=CodexImplementTaskHandler(runner),
        ),
        ToolDefinition(
            name="codex.review_pull_request",
            version="1",
            description="Analyze a pull request internally without publishing a review.",
            agent_types=frozenset({"development"}),
            risk_level=RiskLevel.GREEN,
            timeout_seconds=settings.codex_timeout_seconds,
            max_retries=0,
            requires_approval=False,
            input_schema=CodexReviewPullRequestInput,
            output_schema=CodexReviewOutput,
            handler=CodexReviewPullRequestHandler(runner),
        ),
        ToolDefinition(
            name="codex.fix_pull_request",
            version="1",
            description="Apply approved fixes to the existing branch of a pull request.",
            agent_types=frozenset({"development"}),
            risk_level=RiskLevel.YELLOW,
            timeout_seconds=settings.codex_timeout_seconds,
            max_retries=0,
            requires_approval=True,
            input_schema=CodexFixPullRequestInput,
            output_schema=CodexImplementationOutput,
            handler=CodexFixPullRequestHandler(runner),
        ),
    ]


def _run_id(context: ExecutionContext):
    if context.integration_run_id is None:
        raise CodexValidationError("CodexRun context is missing")
    return context.integration_run_id
