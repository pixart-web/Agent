import logging
import socket
import time
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.execution.context import ExecutionContext
from app.execution.context_safety import sanitize_execution_payload
from app.execution.exceptions import ExecutionError, ToolTimeoutError
from app.execution.policies import RetryPolicy, action_fingerprint
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.integrations.credentials import CredentialProvider, EnvironmentCredentialProvider
from app.models.command import Command
from app.models.outbox_event import OutboxEvent
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import (
    ActorType,
    ApprovalStatus,
    CommandStatus,
    OutboxStatus,
    RiskLevel,
    TaskActionStatus,
    TaskExecutionStatus,
)
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.audit_service import AuditService
from app.services.execution_state_service import ExecutionStateService

logger = logging.getLogger(__name__)


class ExecutionWorker:
    def __init__(
        self,
        session_factory: sessionmaker,
        *,
        registry: ToolRegistry | None = None,
        retry_policy: RetryPolicy,
        worker_id: str | None = None,
        credential_provider: CredentialProvider | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.registry = registry or build_tool_registry()
        self.retry_policy = retry_policy
        self.worker_id = worker_id or socket.gethostname()
        self.credential_provider = credential_provider or EnvironmentCredentialProvider()

    def execute(self, execution_id: UUID) -> TaskExecution | None:
        claimed = self._claim(execution_id)
        if claimed is None:
            return None
        execution, action, task, plan, command, context = claimed
        started = time.perf_counter()
        try:
            definition = self.registry.get(execution.tool_name, execution.tool_version)
            payload = self.registry.validate_input(
                definition, execution.input_payload, task.agent_id
            )
            output = definition.handler.execute(context, payload)
            validated_output = definition.output_schema.model_validate(output)
        except SoftTimeLimitExceeded:
            duration_ms = round((time.perf_counter() - started) * 1000)
            return self._fail(
                execution_id,
                ToolTimeoutError("Tool execution exceeded its timeout"),
                duration_ms,
                definition.max_retries if "definition" in locals() else 0,
            )
        except Exception as error:
            duration_ms = round((time.perf_counter() - started) * 1000)
            return self._fail(
                execution_id,
                error,
                duration_ms,
                definition.max_retries if "definition" in locals() else 0,
            )
        duration_ms = round((time.perf_counter() - started) * 1000)
        return self._succeed(execution_id, validated_output.model_dump(mode="json"), duration_ms)

    def _claim(self, execution_id: UUID):
        with self.session_factory() as session:
            repository = ExecutionRepository(session)
            execution = repository.get_execution_for_update(execution_id)
            if execution is None:
                return None
            if execution.status not in {
                TaskExecutionStatus.QUEUED,
                TaskExecutionStatus.RETRY_SCHEDULED,
            }:
                return None
            action = session.scalar(
                select(TaskAction)
                .where(TaskAction.id == execution.task_action_id)
                .with_for_update(of=TaskAction)
            )
            task = session.scalar(
                select(Task).where(Task.id == execution.task_id).with_for_update(of=Task)
            )
            if action is None or task is None or action.status == TaskActionStatus.CANCELLED:
                execution.status = TaskExecutionStatus.CANCELLED
                execution.completed_at = utc_now()
                session.commit()
                return None
            if action.status != TaskActionStatus.QUEUED:
                return self._cancel_invalid(session, execution, "action_not_queued")
            plan = session.scalar(
                select(Plan).where(Plan.id == task.plan_id).with_for_update(of=Plan)
            )
            command = session.scalar(
                select(Command).where(Command.id == plan.command_id).with_for_update(of=Command)
            )
            definition = self.registry.get(action.tool_name, action.tool_version)
            if command.status == CommandStatus.CANCELLED:
                return self._cancel_invalid(session, execution, "command_cancelled")
            current_fingerprint = action_fingerprint(
                action.tool_name,
                action.tool_version,
                action.input_payload,
                action.risk_level,
            )
            if current_fingerprint != action.action_fingerprint:
                return self._cancel_invalid(session, execution, "action_fingerprint_changed")
            if definition.requires_approval or action.risk_level != RiskLevel.GREEN:
                approval = repository.approved_approval_for_action(action.id, current_fingerprint)
                if approval is None or approval.status != ApprovalStatus.APPROVED:
                    return self._cancel_invalid(session, execution, "approval_missing")
            now = utc_now()
            execution.status = TaskExecutionStatus.RUNNING
            execution.started_at = now
            execution.worker_id = self.worker_id
            action.status = TaskActionStatus.RUNNING
            state = ExecutionStateService(session)
            state.mark_task_running(task, plan, command, action.correlation_id)
            AuditService(session).record(
                actor_type=ActorType.WORKER,
                actor_id=None,
                event_type="execution_started",
                resource_type="task_execution",
                resource_id=execution.id,
                metadata={
                    "task_id": str(task.id),
                    "action_id": str(action.id),
                    "tool": action.tool_name,
                    "attempt": execution.attempt_number,
                    "worker_id": self.worker_id,
                },
                correlation_id=action.correlation_id,
            )
            context = ExecutionContext(
                user_id=command.user_id,
                command_id=command.id,
                task_id=task.id,
                action_id=action.id,
                execution_id=execution.id,
                correlation_id=action.correlation_id,
                credentials=self.credential_provider,
            )
            session.commit()
            logger.info(
                "execution_started",
                extra={
                    "execution_id": str(execution.id),
                    "task_id": str(task.id),
                    "action_id": str(action.id),
                    "tool": execution.tool_name,
                    "duration": None,
                    "attempt": execution.attempt_number,
                    "correlation_id": str(action.correlation_id),
                },
            )
            session.expunge(execution)
            session.expunge(action)
            session.expunge(task)
            session.expunge(plan)
            session.expunge(command)
            return execution, action, task, plan, command, context

    @staticmethod
    def _cancel_invalid(session: Session, execution: TaskExecution, code: str):
        execution.status = TaskExecutionStatus.CANCELLED
        execution.error_code = code
        execution.error_message = "Execution safety validation failed"
        execution.completed_at = utc_now()
        session.commit()
        return None

    def _succeed(
        self, execution_id: UUID, output_payload: dict[str, object], duration_ms: int
    ) -> TaskExecution:
        with self.session_factory() as session:
            repository = ExecutionRepository(session)
            execution = repository.get_execution_for_update(execution_id)
            action, task, plan, command = self._locked_context(session, execution)
            execution.status = TaskExecutionStatus.SUCCEEDED
            execution.output_payload = sanitize_execution_payload(output_payload)
            execution.completed_at = utc_now()
            execution.duration_ms = duration_ms
            action.status = TaskActionStatus.COMPLETED
            state = ExecutionStateService(session)
            state.complete_task_if_ready(task, plan, command, action.correlation_id)
            AuditService(session).record(
                actor_type=ActorType.WORKER,
                actor_id=None,
                event_type="execution_succeeded",
                resource_type="task_execution",
                resource_id=execution.id,
                metadata={
                    "task_id": str(task.id),
                    "action_id": str(action.id),
                    "duration_ms": duration_ms,
                    "attempt": execution.attempt_number,
                },
                correlation_id=action.correlation_id,
            )
            github_event = self._github_audit_event(action.tool_name)
            if github_event is not None:
                metadata: dict[str, object] = {
                    "tool": action.tool_name,
                    "execution_id": str(execution.id),
                }
                for key in ("repository", "path", "branch", "ref"):
                    value = action.input_payload.get(key)
                    if value is not None:
                        metadata[key] = value
                number = output_payload.get("issue_number") or output_payload.get("number")
                if number is not None:
                    if "pull_request" in action.tool_name:
                        metadata["pull_request_number"] = number
                    elif "issue" in action.tool_name:
                        metadata["issue_number"] = number
                AuditService(session).record(
                    actor_type=ActorType.WORKER,
                    actor_id=None,
                    event_type=github_event,
                    resource_type="github_operation",
                    resource_id=execution.id,
                    metadata=metadata,
                    correlation_id=action.correlation_id,
                )
            session.commit()
            session.refresh(execution)
            session.expunge(execution)
            logger.info(
                "execution_completed",
                extra={
                    "execution_id": str(execution.id),
                    "task_id": str(task.id),
                    "action_id": str(action.id),
                    "tool": execution.tool_name,
                    "duration": duration_ms,
                    "attempt": execution.attempt_number,
                    "correlation_id": str(action.correlation_id),
                },
            )
            return execution

    def _fail(
        self,
        execution_id: UUID,
        error: Exception,
        duration_ms: int,
        tool_max_retries: int,
    ) -> TaskExecution:
        with self.session_factory() as session:
            repository = ExecutionRepository(session)
            execution = repository.get_execution_for_update(execution_id)
            action, task, plan, command = self._locked_context(session, execution)
            retryable = isinstance(error, ExecutionError) and error.retryable
            decision = self.retry_policy.decide(
                attempt_number=execution.attempt_number,
                tool_max_retries=tool_max_retries,
                retry_after_seconds=getattr(error, "retry_after_seconds", None),
                retryable=retryable,
            )
            execution.status = TaskExecutionStatus.FAILED
            execution.error_code = (
                error.code if isinstance(error, ExecutionError) else type(error).__name__
            )
            execution.error_message = self._safe_error(error)
            execution.completed_at = utc_now()
            execution.duration_ms = duration_ms
            audit = AuditService(session)
            audit.record(
                actor_type=ActorType.WORKER,
                actor_id=None,
                event_type="execution_failed",
                resource_type="task_execution",
                resource_id=execution.id,
                metadata={
                    "task_id": str(task.id),
                    "action_id": str(action.id),
                    "error_code": execution.error_code,
                    "attempt": execution.attempt_number,
                },
                correlation_id=action.correlation_id,
            )
            if decision.retry:
                retry = TaskExecution(
                    task_id=task.id,
                    task_action_id=action.id,
                    attempt_number=execution.attempt_number + 1,
                    status=TaskExecutionStatus.RETRY_SCHEDULED,
                    tool_name=action.tool_name,
                    tool_version=action.tool_version,
                    input_payload=action.input_payload,
                    queued_at=utc_now(),
                    correlation_id=action.correlation_id,
                )
                repository.add_execution(retry)
                session.flush()
                from datetime import timedelta

                OutboxRepository(session).add(
                    OutboxEvent(
                        event_type="execution.requested",
                        aggregate_type="task_execution",
                        aggregate_id=retry.id,
                        payload={
                            "execution_id": str(retry.id),
                            "correlation_id": str(action.correlation_id),
                        },
                        status=OutboxStatus.PENDING,
                        next_attempt_at=utc_now() + timedelta(seconds=decision.delay_seconds),
                    )
                )
                action.status = TaskActionStatus.QUEUED
                audit.record(
                    actor_type=ActorType.SYSTEM,
                    actor_id=None,
                    event_type="execution_retry_scheduled",
                    resource_type="task_execution",
                    resource_id=retry.id,
                    metadata={
                        "previous_execution_id": str(execution.id),
                        "attempt": retry.attempt_number,
                        "delay_seconds": decision.delay_seconds,
                    },
                    correlation_id=action.correlation_id,
                )
            else:
                action.status = TaskActionStatus.FAILED
                ExecutionStateService(session).fail_task(
                    task,
                    plan,
                    command,
                    action.correlation_id,
                    execution.error_message or "Execution failed",
                )
            session.commit()
            session.refresh(execution)
            session.expunge(execution)
            logger.warning(
                "execution_failed",
                extra={
                    "execution_id": str(execution.id),
                    "task_id": str(task.id),
                    "action_id": str(action.id),
                    "tool": execution.tool_name,
                    "duration": duration_ms,
                    "attempt": execution.attempt_number,
                    "correlation_id": str(action.correlation_id),
                    "error_code": execution.error_code,
                },
            )
            return execution

    @staticmethod
    def _locked_context(session: Session, execution: TaskExecution):
        action = session.scalar(
            select(TaskAction)
            .where(TaskAction.id == execution.task_action_id)
            .with_for_update(of=TaskAction)
        )
        task = session.scalar(
            select(Task).where(Task.id == execution.task_id).with_for_update(of=Task)
        )
        plan = session.scalar(select(Plan).where(Plan.id == task.plan_id).with_for_update(of=Plan))
        command = session.scalar(
            select(Command).where(Command.id == plan.command_id).with_for_update(of=Command)
        )
        return action, task, plan, command

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, ExecutionError):
            return str(error)[:500] or "Execution failed"
        return "Tool execution failed"

    @staticmethod
    def _github_audit_event(tool_name: str) -> str | None:
        return {
            "github.get_repository": "github_repository_read",
            "github.list_branches": "github_repository_read",
            "github.list_pull_requests": "github_repository_read",
            "github.get_pull_request": "github_repository_read",
            "github.list_issues": "github_repository_read",
            "github.get_issue": "github_repository_read",
            "github.read_file": "github_file_read",
            "github.create_issue": "github_issue_created",
            "github.comment_issue": "github_issue_commented",
            "github.create_branch": "github_branch_created",
            "github.create_or_update_file": "github_file_written",
            "github.open_pull_request": "github_pull_request_opened",
        }.get(tool_name)
