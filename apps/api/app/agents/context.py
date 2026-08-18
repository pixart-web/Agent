from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_dependency import TaskDependency
from app.models.task_execution import TaskExecution


@dataclass(frozen=True)
class AgentTaskContext:
    user_id: UUID
    command_id: UUID
    correlation_id: UUID
    command_input: str
    plan_objective: str
    task_id: UUID
    task_title: str
    task_instructions: str
    task_risk: str
    dependencies: tuple[str, ...]
    available_tools: tuple[str, ...]
    previous_attempts: tuple[str, ...]
    feedback: str | None
    max_context_chars: int

    def user_prompt(self) -> str:
        content = (
            f"Plan objective: {self.plan_objective}\n"
            f"Task: {self.task_title}\nInstructions: {self.task_instructions}\n"
            f"Task risk: {self.task_risk}\nDependencies: {list(self.dependencies)}\n"
            f"Available tools: {list(self.available_tools)}\n"
            f"Previous attempts: {list(self.previous_attempts)}\n"
            f"User feedback: {self.feedback or 'none'}"
        )
        return content[: self.max_context_chars]


class AgentContextBuilder:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build(
        self,
        task: Task,
        user_id: UUID,
        allowed_tools: frozenset[str],
        feedback: str | None,
        max_context_chars: int,
    ) -> AgentTaskContext:
        plan = self.session.get(Plan, task.plan_id)
        command = self.session.scalar(
            select(Command).where(Command.id == plan.command_id, Command.user_id == user_id)
        )
        dependencies = tuple(
            self.session.scalars(
                select(Task.title)
                .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
                .where(TaskDependency.task_id == task.id)
                .order_by(Task.sequence)
            )
        )
        attempts = tuple(
            self.session.scalars(
                select(TaskExecution.error_code)
                .join(TaskAction, TaskAction.id == TaskExecution.task_action_id)
                .where(TaskAction.task_id == task.id, TaskExecution.error_code.is_not(None))
                .order_by(TaskExecution.created_at.desc())
                .limit(10)
            )
        )
        return AgentTaskContext(
            user_id=user_id,
            command_id=command.id,
            correlation_id=command.correlation_id,
            command_input=command.input[:2000],
            plan_objective=plan.objective,
            task_id=task.id,
            task_title=task.title,
            task_instructions=task.instructions,
            task_risk=task.risk_level.value,
            dependencies=dependencies,
            available_tools=tuple(sorted(allowed_tools)),
            previous_attempts=attempts,
            feedback=feedback,
            max_context_chars=max_context_chars,
        )
