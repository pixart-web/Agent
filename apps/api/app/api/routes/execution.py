from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.workflow_responses import raise_workflow_http_error
from app.db.session import get_db
from app.models.user import User
from app.models.workflow_enums import ApprovalStatus, RiskLevel, TaskExecutionStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.command_repository import CommandRepository
from app.schemas.execution import (
    ApprovalDecision,
    ApprovalRequestRead,
    AuditLogRead,
    DispatchResponse,
    PlanProgressRead,
    TaskActionCreate,
    TaskActionRead,
    TaskDependencyCreate,
    TaskDependencyRead,
    TaskExecutionRead,
)
from app.schemas.task import TaskRead
from app.services.approval_service import ApprovalService
from app.services.dependency_service import DependencyService
from app.services.execution_service import ExecutionService
from app.services.execution_state_service import ExecutionStateService
from app.services.task_scheduler_service import TaskSchedulerService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

router = APIRouter(tags=["execution"])


def _raise(error: Exception) -> None:
    raise_workflow_http_error(error)


@router.post(
    "/tasks/{task_id}/actions",
    response_model=TaskActionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_action(
    task_id: UUID,
    data: TaskActionCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskActionRead:
    try:
        action = ExecutionService(db).create_action(task_id, user.id, data)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return TaskActionRead.model_validate(action)


@router.get("/tasks/{task_id}/actions", response_model=list[TaskActionRead])
def list_actions(
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskActionRead]:
    try:
        actions = ExecutionService(db).list_for_task(task_id, user.id)
    except WorkflowNotFoundError as error:
        _raise(error)
    return [TaskActionRead.model_validate(action) for action in actions]


@router.get("/actions/{action_id}", response_model=TaskActionRead)
def get_action(
    action_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskActionRead:
    try:
        action = ExecutionService(db).get_owned(action_id, user.id)
    except WorkflowNotFoundError as error:
        _raise(error)
    return TaskActionRead.model_validate(action)


@router.post("/actions/{action_id}/dispatch", response_model=DispatchResponse)
def dispatch_action(
    action_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DispatchResponse:
    try:
        result = ExecutionService(db).dispatch(action_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return DispatchResponse(
        action=TaskActionRead.model_validate(result.action),
        execution=(
            TaskExecutionRead.model_validate(result.execution)
            if result.execution is not None
            else None
        ),
        approval=(
            ApprovalRequestRead.model_validate(result.approval)
            if result.approval is not None
            else None
        ),
    )


@router.post("/actions/{action_id}/cancel", response_model=TaskActionRead)
def cancel_action(
    action_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskActionRead:
    try:
        action = ExecutionService(db).cancel(action_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return TaskActionRead.model_validate(action)


@router.get("/actions/{action_id}/executions", response_model=list[TaskExecutionRead])
def list_action_executions(
    action_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskExecutionRead]:
    try:
        executions = ExecutionService(db).list_executions(action_id, user.id)
    except WorkflowNotFoundError as error:
        _raise(error)
    return [TaskExecutionRead.model_validate(item) for item in executions]


@router.get("/executions/{execution_id}", response_model=TaskExecutionRead)
def get_execution(
    execution_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskExecutionRead:
    try:
        execution = ExecutionService(db).get_execution(execution_id, user.id)
    except WorkflowNotFoundError as error:
        _raise(error)
    return TaskExecutionRead.model_validate(execution)


@router.get("/approvals", response_model=list[ApprovalRequestRead])
def list_approvals(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    approval_status: Annotated[ApprovalStatus | None, Query(alias="status")] = None,
    risk_level: RiskLevel | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ApprovalRequestRead]:
    approvals = ApprovalService(db).list_owned(
        user.id,
        status=approval_status,
        risk_level=risk_level,
        limit=limit,
        offset=offset,
    )
    return [ApprovalRequestRead.model_validate(item) for item in approvals]


@router.get("/approvals/{approval_id}", response_model=ApprovalRequestRead)
def get_approval(
    approval_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ApprovalRequestRead:
    try:
        approval = ApprovalService(db).get_owned(approval_id, user.id)
    except WorkflowNotFoundError as error:
        _raise(error)
    return ApprovalRequestRead.model_validate(approval)


@router.post("/approvals/{approval_id}/approve", response_model=DispatchResponse)
def approve_action(
    approval_id: UUID,
    data: ApprovalDecision,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DispatchResponse:
    try:
        approval, execution = ApprovalService(db).approve(approval_id, user.id, data)
        action = ExecutionService(db).get_owned(approval.task_action_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return DispatchResponse(
        action=TaskActionRead.model_validate(action),
        execution=TaskExecutionRead.model_validate(execution),
        approval=ApprovalRequestRead.model_validate(approval),
    )


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestRead)
def reject_action(
    approval_id: UUID,
    data: ApprovalDecision,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ApprovalRequestRead:
    try:
        approval = ApprovalService(db).reject(approval_id, user.id, data)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return ApprovalRequestRead.model_validate(approval)


@router.post(
    "/tasks/{task_id}/dependencies",
    response_model=TaskDependencyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_dependency(
    task_id: UUID,
    data: TaskDependencyCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskDependencyRead:
    try:
        dependency = DependencyService(db).create(task_id, user.id, data.depends_on_task_id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return TaskDependencyRead.model_validate(dependency)


@router.get("/tasks/{task_id}/dependencies", response_model=list[TaskDependencyRead])
def list_dependencies(
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TaskDependencyRead]:
    try:
        dependencies = DependencyService(db).list_owned(task_id, user.id)
    except WorkflowNotFoundError as error:
        _raise(error)
    return [TaskDependencyRead.model_validate(item) for item in dependencies]


@router.post("/tasks/{task_id}/schedule", response_model=TaskRead)
def schedule_task(
    task_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskRead:
    try:
        task = TaskSchedulerService(db).schedule(task_id, user.id)
    except (WorkflowNotFoundError, WorkflowConflictError) as error:
        _raise(error)
    return TaskRead.model_validate(task)


@router.get("/plans/{plan_id}/progress", response_model=PlanProgressRead)
def get_plan_progress(
    plan_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanProgressRead:
    from app.repositories.plan_repository import PlanRepository

    if PlanRepository(db).get_owned(plan_id, user.id) is None:
        _raise(WorkflowNotFoundError("Plan not found"))
    return PlanProgressRead.model_validate(ExecutionStateService(db).progress(plan_id))


@router.get("/commands/{command_id}/activity", response_model=list[AuditLogRead])
def command_activity(
    command_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AuditLogRead]:
    command = CommandRepository(db).get_owned(command_id, user.id)
    if command is None:
        _raise(WorkflowNotFoundError("Command not found"))
    if command.correlation_id is None:
        return []
    logs = AuditRepository(db).list_for_correlation_owned(command.correlation_id, user.id)

    return [AuditLogRead.model_validate(log) for log in logs]


@router.get("/executions", response_model=list[TaskExecutionRead])
def list_executions(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    execution_status: Annotated[TaskExecutionStatus | None, Query(alias="status")] = None,
    agent: str | None = None,
    risk: RiskLevel | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskExecutionRead]:
    executions = ExecutionService(db).list_owned_executions(
        user.id,
        status=execution_status,
        agent_id=agent,
        risk_level=risk,
        limit=limit,
        offset=offset,
    )
    return [TaskExecutionRead.model_validate(item) for item in executions]
