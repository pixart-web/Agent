from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.execution.context_safety import sanitize_execution_payload
from app.execution.policies import ExecutionRiskPolicy, action_fingerprint, maximum_risk
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.models.approval_request import ApprovalRequest
from app.models.task_action import TaskAction
from app.models.workflow_enums import (
    ActorType,
    ApprovalStatus,
    RiskLevel,
    TaskActionStatus,
    TaskStatus,
)
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.execution import TaskActionCreate
from app.services.audit_service import AuditService
from app.services.dependency_service import DependencyService
from app.services.execution_queue_service import ExecutionQueueService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


@dataclass(frozen=True)
class DispatchResult:
    action: TaskAction
    execution: object | None
    approval: ApprovalRequest | None


class ExecutionService:
    def __init__(self, session: Session, registry: ToolRegistry | None = None) -> None:
        self.session = session
        self.registry = registry or build_tool_registry()
        self.tasks = TaskRepository(session)
        self.executions = ExecutionRepository(session)
        self.dependencies = DependencyService(session)
        self.queue = ExecutionQueueService(session)
        self.audit = AuditService(session)
        self.risk_policy = ExecutionRiskPolicy()

    def create_action(self, task_id: UUID, user_id: UUID, data: TaskActionCreate) -> TaskAction:
        try:
            if data.created_by_type != ActorType.USER:
                raise WorkflowConflictError("Public action creation must be attributed to the user")
            task = self.tasks.get_owned_for_update(task_id, user_id)
            if task is None:
                raise WorkflowNotFoundError("Task not found")
            if task.status not in {
                TaskStatus.READY,
                TaskStatus.BLOCKED,
                TaskStatus.WAITING_APPROVAL,
            }:
                raise WorkflowConflictError("Actions require a ready task")
            definition = self.registry.get(data.tool_name, data.tool_version)
            validated = self.registry.validate_input(definition, data.input_payload, task.agent_id)
            requested_risk = data.risk_level or RiskLevel.GREEN
            effective_risk = maximum_risk(
                task.risk_level,
                requested_risk,
                definition.risk_level,
                self.risk_policy.evaluate(data.input_payload),
            )
            payload = sanitize_execution_payload(validated.model_dump(mode="json"))
            correlation_id = self._correlation_id(task_id, user_id)
            fingerprint = action_fingerprint(
                definition.name, definition.version, payload, effective_risk
            )
            action = TaskAction(
                task_id=task.id,
                tool_name=definition.name,
                tool_version=definition.version,
                input_payload=payload,
                risk_level=effective_risk,
                status=TaskActionStatus.PROPOSED,
                created_by_type=data.created_by_type,
                created_by_id=user_id if data.created_by_type == ActorType.USER else None,
                action_fingerprint=fingerprint,
                correlation_id=correlation_id,
            )
            self.executions.add_action(action)
            self.session.flush()
            self.audit.record(
                actor_type=data.created_by_type,
                actor_id=action.created_by_id,
                event_type="action_created",
                resource_type="task_action",
                resource_id=action.id,
                metadata={
                    "task_id": str(task.id),
                    "tool": action.tool_name,
                    "risk": action.risk_level.value,
                },
                correlation_id=correlation_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(action)
        return action

    def list_for_task(self, task_id: UUID, user_id: UUID) -> list[TaskAction]:
        if self.tasks.get_owned(task_id, user_id) is None:
            raise WorkflowNotFoundError("Task not found")
        return self.executions.list_actions_for_task_owned(task_id, user_id)

    def get_owned(self, action_id: UUID, user_id: UUID) -> TaskAction:
        action = self.executions.get_action_owned(action_id, user_id)
        if action is None:
            raise WorkflowNotFoundError("Action not found")
        return action

    def dispatch(self, action_id: UUID, user_id: UUID) -> DispatchResult:
        try:
            action = self.executions.get_action_owned_for_update(action_id, user_id)
            if action is None:
                raise WorkflowNotFoundError("Action not found")
            if action.status not in {TaskActionStatus.PROPOSED, TaskActionStatus.APPROVED}:
                raise WorkflowConflictError("Action cannot be dispatched from its current state")
            task = self.tasks.get_owned_for_update(action.task_id, user_id)
            if task is None:
                raise WorkflowNotFoundError("Task not found")
            if task.status not in {
                TaskStatus.READY,
                TaskStatus.BLOCKED,
                TaskStatus.WAITING_APPROVAL,
            }:
                raise WorkflowConflictError("Task is not ready for execution")
            if not self.dependencies.satisfied(task.id):
                task.status = TaskStatus.BLOCKED
                self.session.commit()
                raise WorkflowConflictError("Task dependencies are not completed")
            definition = self.registry.get(action.tool_name, action.tool_version)
            self.registry.validate_input(definition, action.input_payload, task.agent_id)
            effective_risk = maximum_risk(task.risk_level, action.risk_level, definition.risk_level)
            current_fingerprint = action_fingerprint(
                action.tool_name,
                action.tool_version,
                action.input_payload,
                effective_risk,
            )
            action.risk_level = effective_risk
            action.action_fingerprint = current_fingerprint
            requires_approval = definition.requires_approval or effective_risk != RiskLevel.GREEN
            if requires_approval and action.status != TaskActionStatus.APPROVED:
                approval = self._request_approval(action, task, user_id)
                self.session.commit()
                return DispatchResult(action, None, approval)
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
        self.session.refresh(action)
        self.session.refresh(execution)
        return DispatchResult(action, execution, None)

    def cancel(self, action_id: UUID, user_id: UUID) -> TaskAction:
        try:
            action = self.executions.get_action_owned_for_update(action_id, user_id)
            if action is None:
                raise WorkflowNotFoundError("Action not found")
            if action.status not in {
                TaskActionStatus.PROPOSED,
                TaskActionStatus.WAITING_APPROVAL,
                TaskActionStatus.APPROVED,
                TaskActionStatus.QUEUED,
            }:
                raise WorkflowConflictError("Running or terminal action cannot be cancelled")
            action.status = TaskActionStatus.CANCELLED
            self.executions.cancel_pending_approvals(action.id, utc_now())
            self.audit.record(
                actor_type=ActorType.USER,
                actor_id=user_id,
                event_type="action_cancelled",
                resource_type="task_action",
                resource_id=action.id,
                metadata={"task_id": str(action.task_id)},
                correlation_id=action.correlation_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(action)
        return action

    def list_executions(self, action_id: UUID, user_id: UUID) -> list:
        if self.executions.get_action_owned(action_id, user_id) is None:
            raise WorkflowNotFoundError("Action not found")
        return self.executions.list_executions_for_action_owned(action_id, user_id)

    def get_execution(self, execution_id: UUID, user_id: UUID):
        execution = self.executions.get_execution_owned(execution_id, user_id)
        if execution is None:
            raise WorkflowNotFoundError("Execution not found")
        return execution

    def _request_approval(self, action: TaskAction, task, user_id: UUID) -> ApprovalRequest:
        existing = self.executions.pending_approval_for_action(action.id)
        if existing is not None:
            return existing
        approval = ApprovalRequest(
            user_id=user_id,
            task_id=task.id,
            task_action_id=action.id,
            risk_level=action.risk_level,
            title=f"Kiko requests permission: {action.tool_name}",
            description=(
                f"Allow {action.tool_name} for task '{task.title}'. "
                "No external service is contacted by the built-in simulation tools."
            ),
            status=ApprovalStatus.PENDING,
            action_fingerprint=action.action_fingerprint,
            correlation_id=action.correlation_id,
        )
        self.executions.add_approval(approval)
        action.status = TaskActionStatus.WAITING_APPROVAL
        task.status = TaskStatus.WAITING_APPROVAL
        self.session.flush()
        self.audit.record(
            actor_type=ActorType.KIKO,
            actor_id=None,
            event_type="approval_requested",
            resource_type="approval_request",
            resource_id=approval.id,
            metadata={
                "task_id": str(task.id),
                "action_id": str(action.id),
                "risk": action.risk_level.value,
            },
            correlation_id=action.correlation_id,
        )
        return approval

    def _correlation_id(self, task_id: UUID, user_id: UUID) -> UUID:
        from sqlalchemy import select

        from app.models.command import Command
        from app.models.plan import Plan
        from app.models.task import Task

        command = self.session.scalar(
            select(Command)
            .join(Plan, Plan.command_id == Command.id)
            .join(Task, Task.plan_id == Plan.id)
            .where(Task.id == task_id, Command.user_id == user_id)
            .with_for_update(of=Command)
        )
        if command is None:
            raise WorkflowNotFoundError("Task not found")
        if command.correlation_id is None:
            command.correlation_id = uuid4()
        return command.correlation_id

    def list_owned_executions(self, user_id: UUID, **filters):
        return self.executions.list_executions_owned(user_id, **filters)
