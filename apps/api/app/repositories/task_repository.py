from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: Task) -> None:
        self.session.add(task)

    def get_owned(self, task_id: UUID, user_id: UUID) -> Task | None:
        statement = (
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.id == task_id, Command.user_id == user_id)
        )
        return self.session.scalar(statement)

    def list_for_plan_owned(self, plan_id: UUID, user_id: UUID) -> list[Task]:
        statement = (
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.plan_id == plan_id, Command.user_id == user_id)
            .order_by(Task.sequence, Task.created_at, Task.id)
        )
        return list(self.session.scalars(statement))
