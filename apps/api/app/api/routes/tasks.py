from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskDetail,
    TaskRead,
    TaskStatusHistoryRead,
    TaskTransition,
    TaskUpdate,
)
from app.services.task_service import TaskDetailData, TaskService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(tags=["tasks"])


def _task_detail(data: TaskDetailData) -> TaskDetail:
    return TaskDetail(
        **TaskRead.model_validate(data.task).model_dump(),
        history=[TaskStatusHistoryRead.model_validate(history) for history in data.history],
    )


@router.post(
    "/plans/{plan_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    plan_id: UUID,
    data: TaskCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskRead:
    try:
        task = TaskService(db).create(plan_id, user.id, data)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return TaskRead.model_validate(task)


@router.get("/plans/{plan_id}/tasks", response_model=list[TaskRead])
def list_tasks(
    plan_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskRead]:
    try:
        tasks = TaskService(db).list_for_plan_owned(plan_id, user.id)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return [TaskRead.model_validate(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskDetail:
    try:
        detail = TaskService(db).get_detail(task_id, user.id)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return _task_detail(detail)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskRead:
    try:
        task = TaskService(db).update(task_id, user.id, data)
    except WorkflowNotFoundError as error:
        raise_workflow_http_error(error)
    return TaskRead.model_validate(task)


@router.post("/tasks/{task_id}/transition", response_model=TaskDetail)
def transition_task(
    task_id: UUID,
    data: TaskTransition,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskDetail:
    try:
        detail = TaskService(db).transition(task_id, user.id, data)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        raise_workflow_http_error(error)
    return _task_detail(detail)
