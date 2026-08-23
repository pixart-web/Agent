from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.codex_run import CodexRun
from app.models.task_action import TaskAction
from app.models.workflow_enums import ActorType, CodexRunStatus
from app.repositories.codex_run_repository import CodexRunRepository
from app.services.audit_service import AuditService


class CodexRunService:
    def __init__(self, session: Session, *, runner_type: str = "cli") -> None:
        self.session = session
        self.repository = CodexRunRepository(session)
        self.audit = AuditService(session)
        self.runner_type = runner_type

    def ensure_for_action(
        self,
        action: TaskAction,
        user_id: UUID,
        status: CodexRunStatus,
    ) -> CodexRun | None:
        if not action.tool_name.startswith("codex."):
            return None
        existing = self.repository.get_for_action(action.id)
        if existing is not None:
            existing.status = status
            return existing
        payload = action.input_payload
        run = CodexRun(
            task_id=action.task_id,
            task_action_id=action.id,
            user_id=user_id,
            repository=str(payload["repository"]),
            base_branch=str(payload.get("base_branch") or "pull-request"),
            working_branch=(
                str(payload["working_branch"]) if payload.get("working_branch") else None
            ),
            status=status,
            instruction=str(
                payload.get("instructions")
                or payload.get("review_focus")
                or "Review the pull request"
            ),
            acceptance_criteria=list(payload.get("acceptance_criteria") or []),
            runner_type=self.runner_type,
            pull_request_number=(
                int(payload["pull_request_number"])
                if payload.get("pull_request_number") is not None
                else None
            ),
            correlation_id=action.correlation_id,
        )
        self.repository.add(run)
        self.session.flush()
        self.audit.record(
            actor_type=ActorType.KIKO,
            actor_id=None,
            event_type="codex_run_created",
            resource_type="codex_run",
            resource_id=run.id,
            metadata={
                "task_id": str(run.task_id),
                "action_id": str(action.id),
                "repository": run.repository,
                "status": run.status.value,
            },
            correlation_id=run.correlation_id,
        )
        return run

    def cancel_for_action(self, action_id: UUID) -> None:
        run = self.repository.get_for_action_for_update(action_id)
        if run is None or run.status in {
            CodexRunStatus.SUCCEEDED,
            CodexRunStatus.FAILED,
            CodexRunStatus.CANCELLED,
        }:
            return
        run.status = CodexRunStatus.CANCELLED
        run.completed_at = utc_now()
