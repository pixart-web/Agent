from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_status_history import TaskStatusHistory
from app.models.workflow_enums import (
    TERMINAL_COMMAND_STATUSES,
    PlanStatus,
    TaskPriority,
    TaskStatus,
)
from app.repositories.agent_repository import AgentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.task_status_history_repository import (
    TaskStatusHistoryRepository,
)
from app.schemas.task import TaskCreate, TaskTransition, TaskUpdate
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

ALLOWED_TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.READY: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.BLOCKED}),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.BLOCKED,
        }
    ),
    TaskStatus.WAITING_APPROVAL: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.FAILED: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class TaskDetailData:
    task: Task
    plan: Plan
    command: Command
    history: list[TaskStatusHistory]


class TaskService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.agents = AgentRepository(session)
        self.plans = PlanRepository(session)
        self.tasks = TaskRepository(session)
        self.history = TaskStatusHistoryRepository(session)

    def _get_owned(self, task_id: UUID, user_id: UUID) -> Task:
        task = self.tasks.get_owned(task_id, user_id)
        if task is None:
            raise WorkflowNotFoundError("Task not found")
        return task

    def _get_owned_for_update(self, task_id: UUID, user_id: UUID) -> Task:
        task = self.tasks.get_owned_for_update(task_id, user_id)
        if task is None:
            raise WorkflowNotFoundError("Task not found")
        return task

    def _require_agent(self, agent_id: str) -> None:
        if self.agents.get(agent_id) is None:
            raise WorkflowNotFoundError("Agent not found")

    def create(self, plan_id: UUID, user_id: UUID, data: TaskCreate) -> Task:
        try:
            plan_and_command = self.plans.get_owned_with_command_for_update(
                plan_id,
                user_id,
            )
            if plan_and_command is None:
                raise WorkflowNotFoundError("Plan not found")
            plan, command = plan_and_command
            if command.status in TERMINAL_COMMAND_STATUSES:
                raise WorkflowConflictError("A terminal command cannot receive new tasks")
            if not plan.is_current or plan.status != PlanStatus.DRAFT:
                raise WorkflowConflictError("Tasks can only be added to the current draft plan")
            self._require_agent(data.agent_id)

            task = Task(plan_id=plan_id, **data.model_dump())
            self.tasks.add(task)
            self.session.flush()
            self.history.add(
                TaskStatusHistory(
                    task_id=task.id,
                    from_status=None,
                    to_status=TaskStatus.PENDING,
                    changed_by_user_id=user_id,
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(task)
        return task

    def list_for_plan_owned(self, plan_id: UUID, user_id: UUID) -> list[Task]:
        if self.plans.get_owned(plan_id, user_id) is None:
            raise WorkflowNotFoundError("Plan not found")
        return self.tasks.list_for_plan_owned(plan_id, user_id)

    def get_detail(self, task_id: UUID, user_id: UUID) -> TaskDetailData:
        context = self.tasks.get_owned_context(task_id, user_id)
        if context is None:
            raise WorkflowNotFoundError("Task not found")
        task, plan, command = context
        history = self.history.list_for_task_owned(task_id, user_id)
        return TaskDetailData(task=task, plan=plan, command=command, history=history)

    def list_owned(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        agent_id: str | None,
        search: str | None,
    ) -> list[tuple[Task, Plan, Command]]:
        return self.tasks.list_owned(
            user_id,
            limit,
            offset,
            status.value if status else None,
            priority.value if priority else None,
            agent_id,
            search,
        )

    def update(self, task_id: UUID, user_id: UUID, data: TaskUpdate) -> Task:
        try:
            task = self._get_owned_for_update(task_id, user_id)
            values = data.model_dump(exclude_unset=True, exclude_none=True)
            if "due_at" in data.model_fields_set:
                values["due_at"] = data.due_at
            if "agent_id" in values:
                raise WorkflowConflictError("Use the explicit reassign-agent endpoint")
            for field, value in values.items():
                setattr(task, field, value)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(task)
        return task

    def transition(
        self,
        task_id: UUID,
        user_id: UUID,
        data: TaskTransition,
    ) -> TaskDetailData:
        try:
            task = self._get_owned_for_update(task_id, user_id)
            previous_status = task.status
            if data.status not in ALLOWED_TASK_TRANSITIONS[previous_status]:
                raise WorkflowConflictError(
                    f"Task cannot transition from {previous_status.value} to {data.status.value}"
                )

            now = utc_now()
            task.status = data.status
            if data.status == TaskStatus.RUNNING and task.started_at is None:
                task.started_at = now
            if data.status in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                task.completed_at = now
            if data.status == TaskStatus.FAILED:
                task.error_message = data.reason
            if previous_status == TaskStatus.FAILED and data.status == TaskStatus.READY:
                task.completed_at = None
                task.error_message = None

            self.history.add(
                TaskStatusHistory(
                    task_id=task.id,
                    from_status=previous_status,
                    to_status=data.status,
                    changed_by_user_id=user_id,
                    reason=data.reason,
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(task)
        return self.get_detail(task.id, user_id)
