from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_status_history import TaskStatusHistory


class TaskStatusHistoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, history: TaskStatusHistory) -> None:
        self.session.add(history)

    def list_for_task_owned(
        self,
        task_id: UUID,
        user_id: UUID,
    ) -> list[TaskStatusHistory]:
        statement = (
            select(TaskStatusHistory)
            .join(Task, Task.id == TaskStatusHistory.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(TaskStatusHistory.task_id == task_id, Command.user_id == user_id)
            .order_by(TaskStatusHistory.created_at, TaskStatusHistory.id)
        )
        return list(self.session.scalars(statement))
