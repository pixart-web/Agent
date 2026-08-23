from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.task_action import TaskAction
from app.models.workflow_enums import ActorType, CodexRunStatus
from app.repositories.codex_run_repository import CodexRunRepository
from app.services.audit_service import AuditService


class CodexExecutionLifecycle:
    def __init__(self, session: Session) -> None:
        self.repository = CodexRunRepository(session)
        self.audit = AuditService(session)

    def start(self, action: TaskAction) -> UUID | None:
        if not action.tool_name.startswith("codex."):
            return None
        run = self.repository.get_for_action_for_update(action.id)
        if run is None:
            return None
        run.status = CodexRunStatus.RUNNING
        run.started_at = utc_now()
        self.audit.record(
            actor_type=ActorType.WORKER,
            actor_id=None,
            event_type="codex_run_started",
            resource_type="codex_run",
            resource_id=run.id,
            metadata={
                "action_id": str(action.id),
                "repository": run.repository,
                "runner": run.runner_type,
            },
            correlation_id=run.correlation_id,
        )
        return run.id

    def succeed(
        self,
        action: TaskAction,
        output: dict[str, object],
        duration_ms: int,
    ) -> None:
        if not action.tool_name.startswith("codex."):
            return
        run = self.repository.get_for_action_for_update(action.id)
        if run is None:
            return
        run.base_branch = _safe_text(output.get("base_branch"), 200) or run.base_branch
        run.status = CodexRunStatus.SUCCEEDED
        run.completed_at = utc_now()
        run.duration_ms = duration_ms
        run.summary = _safe_text(output.get("summary"), 20_000)
        run.files_changed = _safe_list(output.get("files_changed"))
        run.tests_run = _safe_list(output.get("tests_run"))
        run.tests_passed = (
            bool(output["tests_passed"]) if output.get("tests_passed") is not None else None
        )
        run.commit_sha = _safe_text(output.get("commit_sha"), 40)
        run.working_branch = _safe_text(output.get("branch"), 200) or run.working_branch
        run.pull_request_number = (
            int(output["pull_request_number"])
            if output.get("pull_request_number") is not None
            else run.pull_request_number
        )
        run.pull_request_url = _safe_text(output.get("pull_request_url"), 500)
        run.exit_code = int(output["exit_code"]) if output.get("exit_code") is not None else None
        run.model = _safe_text(output.get("model"), 128)
        metadata: dict[str, object] = {
            "action_id": str(action.id),
            "repository": run.repository,
            "duration_ms": duration_ms,
            "changed_files": len(run.files_changed),
            "tests_run": len(run.tests_run),
        }
        self.audit.record(
            actor_type=ActorType.WORKER,
            actor_id=None,
            event_type="codex_run_succeeded",
            resource_type="codex_run",
            resource_id=run.id,
            metadata=metadata,
            correlation_id=run.correlation_id,
        )
        if action.tool_name == "codex.review_pull_request":
            self.audit.record(
                actor_type=ActorType.WORKER,
                actor_id=None,
                event_type="codex_review_completed",
                resource_type="codex_run",
                resource_id=run.id,
                metadata={
                    "repository": run.repository,
                    "pull_request_number": run.pull_request_number,
                },
                correlation_id=run.correlation_id,
            )
        elif run.commit_sha and run.working_branch:
            self.audit.record(
                actor_type=ActorType.WORKER,
                actor_id=None,
                event_type="codex_branch_pushed",
                resource_type="codex_run",
                resource_id=run.id,
                metadata={
                    "repository": run.repository,
                    "branch": run.working_branch,
                    "commit_sha": run.commit_sha,
                },
                correlation_id=run.correlation_id,
            )

    def fail(
        self,
        action: TaskAction,
        *,
        error_code: str,
        error_message: str,
        duration_ms: int,
    ) -> None:
        if not action.tool_name.startswith("codex."):
            return
        run = self.repository.get_for_action_for_update(action.id)
        if run is None:
            return
        run.status = CodexRunStatus.FAILED
        run.completed_at = utc_now()
        run.duration_ms = duration_ms
        run.error_code = error_code[:128]
        run.error_message = error_message[:500]
        self.audit.record(
            actor_type=ActorType.WORKER,
            actor_id=None,
            event_type="codex_run_failed",
            resource_type="codex_run",
            resource_id=run.id,
            metadata={
                "action_id": str(action.id),
                "repository": run.repository,
                "error_code": run.error_code,
            },
            correlation_id=run.correlation_id,
        )


def _safe_text(value: object, maximum: int) -> str | None:
    return str(value)[:maximum] if value is not None else None


def _safe_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:1000] for item in value]
