from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_dependency import TaskDependency
from app.models.workflow_enums import TaskStatus
from app.repositories.dependency_repository import DependencyRepository
from app.repositories.task_repository import TaskRepository
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


class DependencyService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.dependencies = DependencyRepository(session)
        self.tasks = TaskRepository(session)

    def create(self, task_id: UUID, user_id: UUID, depends_on_task_id: UUID) -> TaskDependency:
        try:
            task = self.tasks.get_owned_for_update(task_id, user_id)
            dependency_task = self.tasks.get_owned(depends_on_task_id, user_id)
            if task is None or dependency_task is None:
                raise WorkflowNotFoundError("Task not found")
            if task.id == dependency_task.id:
                raise WorkflowConflictError("A task cannot depend on itself")
            if task.plan_id != dependency_task.plan_id:
                raise WorkflowConflictError("Dependencies must belong to the same plan")
            graph = self.dependencies.graph_for_plan(task.plan_id)
            graph.setdefault(task.id, set()).add(dependency_task.id)
            if self._has_cycle(graph):
                raise WorkflowConflictError("Task dependency would create a cycle")
            dependency = TaskDependency(task_id=task.id, depends_on_task_id=dependency_task.id)
            self.dependencies.add(dependency)
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError("Task dependency already exists") from error
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(dependency)
        return dependency

    def list_owned(self, task_id: UUID, user_id: UUID) -> list[TaskDependency]:
        if self.tasks.get_owned(task_id, user_id) is None:
            raise WorkflowNotFoundError("Task not found")
        return self.dependencies.list_for_task_owned(task_id, user_id)

    def satisfied(self, task_id: UUID) -> bool:
        ids = self.dependencies.dependency_ids(task_id)
        if not ids:
            return True
        tasks = [self.session.get(Task, item) for item in ids]
        return all(task is not None and task.status == TaskStatus.COMPLETED for task in tasks)

    @staticmethod
    def _has_cycle(graph: dict[UUID, set[UUID]]) -> bool:
        visiting: set[UUID] = set()
        visited: set[UUID] = set()

        def visit(node: UUID) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            if any(visit(dependency) for dependency in graph.get(node, set())):
                return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in graph)
