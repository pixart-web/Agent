from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.execution.policies import action_fingerprint
from app.models.approval_comment import ApprovalComment
from app.models.audit_log import AuditLog
from app.models.knowledge import WorkspaceMember
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.workflow_enums import (
    ActorType,
    ApprovalStatus,
    CodexRunStatus,
    RiskLevel,
    TaskActionStatus,
    TaskStatus,
)
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.execution import ApprovalCommentCreate, ApprovalDecision
from app.services.audit_service import AuditService
from app.services.codex_run_service import CodexRunService
from app.services.execution_queue_service import ExecutionQueueService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError
from app.workspaces.scope import active_workspace_id


class ApprovalService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ExecutionRepository(session)
        self.tasks = TaskRepository(session)
        self.queue = ExecutionQueueService(session)
        self.audit = AuditService(session)
        self.codex_runs = CodexRunService(session)

    def list_owned(self, user_id, **filters):
        self._expire_owned(user_id)
        return self.repository.list_approvals_owned(user_id, **filters)

    def get_owned(self, approval_id: UUID, user_id: UUID):
        self._expire_owned(user_id)
        approval = self.repository.get_approval_owned(approval_id, user_id)
        if approval is None:
            raise WorkflowNotFoundError("Approval not found")
        return approval

    def detail(self, approval_id: UUID, user_id: UUID) -> dict:
        approval = self.get_owned(approval_id, user_id)
        action = self.repository.get_action_owned(approval.task_action_id, user_id)
        task = self.tasks.get_owned(approval.task_id, user_id)
        comments = list(
            self.session.scalars(
                select(ApprovalComment)
                .where(ApprovalComment.approval_id == approval.id)
                .order_by(ApprovalComment.created_at, ApprovalComment.id)
            )
        )
        history = list(
            self.session.scalars(
                select(AuditLog)
                .where(
                    AuditLog.resource_type == "approval_request",
                    AuditLog.resource_id == approval.id,
                )
                .order_by(AuditLog.created_at, AuditLog.id)
            )
        )
        return {
            "approval": approval,
            "action": action,
            "requesting_agent": task.agent_id,
            "target_integration": action.tool_name.split(".", 1)[0],
            "comments": comments,
            "history": history,
        }

    def comment(self, approval_id: UUID, user_id: UUID, data: ApprovalCommentCreate):
        try:
            approval = self.get_owned(approval_id, user_id)
            comment = ApprovalComment(
                approval_id=approval.id, author_user_id=user_id, body=data.body
            )
            self.session.add(comment)
            self.session.flush()
            self.audit.record(
                actor_type=ActorType.USER,
                actor_id=user_id,
                event_type="approval_commented",
                resource_type="approval_request",
                resource_id=approval.id,
                metadata={"comment_id": str(comment.id)},
                correlation_id=approval.correlation_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(comment)
        return comment

    def _expire_owned(self, user_id: UUID) -> None:
        now = utc_now()
        approvals = self.repository.list_approvals_owned(
            user_id,
            status=ApprovalStatus.PENDING,
            risk_level=None,
            limit=100,
            offset=0,
        )
        changed = False
        for approval in approvals:
            if not self._is_expired(approval.expires_at, now):
                continue
            approval.status = ApprovalStatus.EXPIRED
            approval.decided_at = now
            action = self.session.get(TaskAction, approval.task_action_id)
            task = self.session.get(Task, approval.task_id)
            if action is not None and action.status == TaskActionStatus.WAITING_APPROVAL:
                action.status = TaskActionStatus.PROPOSED
            if task is not None and task.status == TaskStatus.WAITING_APPROVAL:
                task.status = TaskStatus.READY
            self.audit.record(
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                event_type="approval_expired",
                resource_type="approval_request",
                resource_id=approval.id,
                metadata={"action_id": str(approval.task_action_id)},
                correlation_id=approval.correlation_id,
            )
            changed = True
        if changed:
            self.session.commit()

    @staticmethod
    def _is_expired(expires_at, now=None) -> bool:
        if expires_at is None:
            return False
        now = now or utc_now()
        if expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        return expires_at <= now

    def approve(self, approval_id: UUID, user_id: UUID, data: ApprovalDecision):
        try:
            approval = self.repository.get_approval_owned_for_update(approval_id, user_id)
            if approval is None:
                raise WorkflowNotFoundError("Approval not found")
            if approval.status != ApprovalStatus.PENDING:
                raise WorkflowConflictError("Approval has already been decided")
            if self._is_expired(approval.expires_at):
                raise WorkflowConflictError("Approval has expired")
            if approval.risk_level == RiskLevel.RED and not data.confirm_high_risk:
                raise WorkflowConflictError("Explicit high-risk confirmation is required")
            workspace_members = self.session.scalar(
                select(func.count(WorkspaceMember.id)).where(
                    WorkspaceMember.workspace_id == active_workspace_id(user_id)
                )
            )
            if (
                approval.risk_level == RiskLevel.RED
                and approval.user_id == user_id
                and workspace_members > 1
            ):
                raise WorkflowConflictError(
                    "High-risk approval requires a different workspace member"
                )
            action = self.repository.get_action_owned_for_update(approval.task_action_id, user_id)
            task = self.tasks.get_owned_for_update(approval.task_id, user_id)
            if action is None or task is None:
                raise WorkflowNotFoundError("Action not found")
            current = action_fingerprint(
                action.tool_name,
                action.tool_version,
                action.input_payload,
                action.risk_level,
            )
            if current != approval.action_fingerprint:
                approval.status = ApprovalStatus.CANCELLED
                approval.decided_at = utc_now()
                self.codex_runs.cancel_for_action(action.id)
                self.session.commit()
                raise WorkflowConflictError(
                    "Action changed after approval was requested; request a new approval"
                )
            now = utc_now()
            approval.status = ApprovalStatus.APPROVED
            approval.decided_at = now
            approval.decided_by_user_id = user_id
            approval.decision_reason = data.reason
            action.status = TaskActionStatus.APPROVED
            task.status = TaskStatus.READY
            self.audit.record(
                actor_type=ActorType.USER,
                actor_id=user_id,
                event_type="approval_approved",
                resource_type="approval_request",
                resource_id=approval.id,
                metadata={"action_id": str(action.id), "risk": action.risk_level.value},
                correlation_id=action.correlation_id,
            )
            execution = self.queue.queue(
                action=action,
                task=task,
                actor_type=ActorType.USER,
                actor_id=user_id,
            )
            self.codex_runs.ensure_for_action(action, user_id, CodexRunStatus.QUEUED)
            self.session.commit()
        except WorkflowConflictError:
            if self.session.in_transaction():
                self.session.rollback()
            raise
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(approval)
        self.session.refresh(execution)
        return approval, execution

    def reject(self, approval_id: UUID, user_id: UUID, data: ApprovalDecision):
        try:
            approval = self.repository.get_approval_owned_for_update(approval_id, user_id)
            if approval is None:
                raise WorkflowNotFoundError("Approval not found")
            if approval.status != ApprovalStatus.PENDING:
                raise WorkflowConflictError("Approval has already been decided")
            if self._is_expired(approval.expires_at):
                raise WorkflowConflictError("Approval has expired")
            action = self.repository.get_action_owned_for_update(approval.task_action_id, user_id)
            task = self.tasks.get_owned_for_update(approval.task_id, user_id)
            if action is None or task is None:
                raise WorkflowNotFoundError("Action not found")
            approval.status = ApprovalStatus.REJECTED
            approval.decided_at = utc_now()
            approval.decided_by_user_id = user_id
            approval.decision_reason = data.reason
            action.status = TaskActionStatus.CANCELLED
            self.codex_runs.cancel_for_action(action.id)
            task.status = TaskStatus.READY
            self.audit.record(
                actor_type=ActorType.USER,
                actor_id=user_id,
                event_type="approval_rejected",
                resource_type="approval_request",
                resource_id=approval.id,
                metadata={"action_id": str(action.id)},
                correlation_id=action.correlation_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(approval)
        return approval
