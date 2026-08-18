from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.execution.policies import action_fingerprint
from app.models.workflow_enums import (
    ActorType,
    ApprovalStatus,
    RiskLevel,
    TaskActionStatus,
    TaskStatus,
)
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.execution import ApprovalDecision
from app.services.audit_service import AuditService
from app.services.execution_queue_service import ExecutionQueueService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


class ApprovalService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ExecutionRepository(session)
        self.tasks = TaskRepository(session)
        self.queue = ExecutionQueueService(session)
        self.audit = AuditService(session)

    def list_owned(self, user_id, **filters):
        return self.repository.list_approvals_owned(user_id, **filters)

    def get_owned(self, approval_id: UUID, user_id: UUID):
        approval = self.repository.get_approval_owned(approval_id, user_id)
        if approval is None:
            raise WorkflowNotFoundError("Approval not found")
        return approval

    def approve(self, approval_id: UUID, user_id: UUID, data: ApprovalDecision):
        try:
            approval = self.repository.get_approval_owned_for_update(approval_id, user_id)
            if approval is None:
                raise WorkflowNotFoundError("Approval not found")
            if approval.status != ApprovalStatus.PENDING:
                raise WorkflowConflictError("Approval has already been decided")
            if approval.risk_level == RiskLevel.RED and not data.confirm_high_risk:
                raise WorkflowConflictError("Explicit high-risk confirmation is required")
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
            action = self.repository.get_action_owned_for_update(approval.task_action_id, user_id)
            task = self.tasks.get_owned_for_update(approval.task_id, user_id)
            if action is None or task is None:
                raise WorkflowNotFoundError("Action not found")
            approval.status = ApprovalStatus.REJECTED
            approval.decided_at = utc_now()
            approval.decided_by_user_id = user_id
            approval.decision_reason = data.reason
            action.status = TaskActionStatus.CANCELLED
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
