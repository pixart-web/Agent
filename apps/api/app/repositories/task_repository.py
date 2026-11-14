from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.workspaces.scope import active_workspace_id


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: Task) -> None:
        self.session.add(task)

    def add_all(self, tasks: list[Task]) -> None:
        self.session.add_all(tasks)

    def get_owned(self, task_id: UUID, user_id: UUID) -> Task | None:
        statement = (
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.id == task_id, Command.workspace_id == active_workspace_id(user_id))
        )
        return self.session.scalar(statement)

    def get_owned_context(self, task_id: UUID, user_id: UUID) -> tuple[Task, Plan, Command] | None:
        statement = (
            select(Task, Plan, Command)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.id == task_id, Command.workspace_id == active_workspace_id(user_id))
        )
        row = self.session.execute(statement).one_or_none()
        return None if row is None else (row[0], row[1], row[2])

    def list_owned(
        self,
        user_id: UUID,
        limit: int,
        offset: int,
        status: str | None,
        priority: str | None,
        agent_id: str | None,
        search: str | None,
    ) -> list[tuple[Task, Plan, Command]]:
        statement = (
            select(Task, Plan, Command)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Command.workspace_id == active_workspace_id(user_id))
        )
        if status is not None:
            statement = statement.where(Task.status == status)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        if agent_id is not None:
            statement = statement.where(Task.agent_id == agent_id)
        if search is not None:
            statement = statement.where(
                or_(
                    Task.title.icontains(search, autoescape=True),
                    Task.instructions.icontains(search, autoescape=True),
                    Command.input.icontains(search, autoescape=True),
                )
            )
        rows = self.session.execute(
            statement.order_by(Task.created_at.desc(), Task.id).offset(offset).limit(limit)
        )
        return [(row[0], row[1], row[2]) for row in rows]

    def get_owned_for_update(self, task_id: UUID, user_id: UUID) -> Task | None:
        statement = (
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.id == task_id, Command.workspace_id == active_workspace_id(user_id))
            .with_for_update(of=Task)
        )
        return self.session.scalar(statement)

    def list_for_plan_owned(self, plan_id: UUID, user_id: UUID) -> list[Task]:
        statement = (
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.plan_id == plan_id, Command.workspace_id == active_workspace_id(user_id))
            .order_by(Task.sequence, Task.created_at, Task.id)
        )
        return list(self.session.scalars(statement))

    def list_for_plan_owned_for_update(self, plan_id: UUID, user_id: UUID) -> list[Task]:
        statement = (
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.plan_id == plan_id, Command.workspace_id == active_workspace_id(user_id))
            .order_by(Task.sequence, Task.id)
            .with_for_update(of=Task)
        )
        return list(self.session.scalars(statement))
