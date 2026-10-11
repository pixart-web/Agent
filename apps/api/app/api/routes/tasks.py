from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.models.workflow_enums import TaskPriority, TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskDetail,
    TaskRead,
    TaskStatusHistoryRead,
    TaskTransition,
    TaskUpdate,
    TaskWorkspaceRead,
)
from app.services.task_service import TaskDetailData, TaskService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(tags=["tasks"])


def _task_detail(data: TaskDetailData) -> TaskDetail:
    return TaskDetail(
        **TaskRead.model_validate(data.task).model_dump(),
        command_id=data.command.id,
        command_input=data.command.input,
        plan_title=data.plan.title,
        history=[TaskStatusHistoryRead.model_validate(history) for history in data.history],
    )


@router.get("/tasks", response_model=list[TaskWorkspaceRead])
def list_workspace_tasks(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    agent_id: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200, pattern=r".*\S.*")] = None,
) -> list[TaskWorkspaceRead]:
    rows = TaskService(db).list_owned(
        user.id,
        limit,
        offset,
        task_status,
        priority,
        agent_id,
        search.strip() if search else None,
    )
    return [
        TaskWorkspaceRead(
            **TaskRead.model_validate(task).model_dump(),
            command_id=command.id,
            command_input=command.input,
            plan_title=plan.title,
        )
        for task, plan, command in rows
    ]


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
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
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
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
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
