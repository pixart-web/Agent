from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_status_history import TaskStatusHistory
from app.models.workflow_enums import TaskStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.task_status_history_repository import TaskStatusHistoryRepository
from app.services.dependency_service import DependencyService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


class TaskSchedulerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tasks = TaskRepository(session)
        self.dependencies = DependencyService(session)
        self.history = TaskStatusHistoryRepository(session)

    def schedule(self, task_id: UUID, user_id: UUID) -> Task:
        try:
            task = self.tasks.get_owned_for_update(task_id, user_id)
            if task is None:
                raise WorkflowNotFoundError("Task not found")
            if task.status not in {TaskStatus.READY, TaskStatus.BLOCKED}:
                raise WorkflowConflictError("Only ready or blocked tasks can be scheduled")
            previous = task.status
            target = (
                TaskStatus.READY if self.dependencies.satisfied(task.id) else TaskStatus.BLOCKED
            )
            task.status = target
            if target != previous:
                self.history.add(
                    TaskStatusHistory(
                        task_id=task.id,
                        from_status=previous,
                        to_status=target,
                        changed_by_user_id=None,
                        reason="Dependency scheduler evaluation",
                    )
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(task)
        return task
