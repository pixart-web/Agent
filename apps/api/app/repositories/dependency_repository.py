from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_dependency import TaskDependency


class DependencyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, dependency: TaskDependency) -> None:
        self.session.add(dependency)

    def list_for_task(self, task_id: UUID) -> list[TaskDependency]:
        return list(
            self.session.scalars(select(TaskDependency).where(TaskDependency.task_id == task_id))
        )

    def list_for_task_owned(self, task_id: UUID, user_id: UUID) -> list[TaskDependency]:
        statement = (
            select(TaskDependency)
            .join(Task, Task.id == TaskDependency.task_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(TaskDependency.task_id == task_id, Command.user_id == user_id)
        )
        return list(self.session.scalars(statement))

    def dependency_ids(self, task_id: UUID) -> set[UUID]:
        return set(
            self.session.scalars(
                select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == task_id)
            )
        )

    def graph_for_plan(self, plan_id: UUID) -> dict[UUID, set[UUID]]:
        task_ids = list(self.session.scalars(select(Task.id).where(Task.plan_id == plan_id)))
        graph = {task_id: set() for task_id in task_ids}
        rows = self.session.execute(
            select(TaskDependency.task_id, TaskDependency.depends_on_task_id)
            .join(Task, Task.id == TaskDependency.task_id)
            .where(Task.plan_id == plan_id)
        )
        for task_id, depends_on in rows:
            graph[task_id].add(depends_on)
        return graph
