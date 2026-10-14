from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.automations.errors import (
    AutomationConflictError,
    AutomationNotFoundError,
    AutomationValidationError,
)
from app.automations.schemas import (
    AutomationCreate,
    AutomationList,
    AutomationRead,
    AutomationRunList,
    AutomationRunRead,
    AutomationTrigger,
    AutomationUpdate,
)
from app.automations.service import AutomationService
from app.commercial.service import CommercialService
from app.db.session import get_db
from app.models.knowledge import WorkspaceMember
from app.models.user import User

router = APIRouter(prefix="/automations", tags=["automations"])


def _service(db: Session) -> AutomationService:
    return AutomationService(sessionmaker(bind=db.get_bind(), expire_on_commit=False))


def _raise(error: Exception) -> None:
    if isinstance(error, AutomationNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, AutomationConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=422, detail=str(error)) from error


def _require_editor(db: Session, user: User) -> None:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace edit permission is required")


@router.post("", response_model=AutomationRead, status_code=status.HTTP_201_CREATED)
def create_automation(
    value: AutomationCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRead:
    _require_editor(db, user)
    decision = CommercialService(db).entitlement(user.active_workspace_id, "automations")
    if not decision.allowed:
        raise HTTPException(status_code=402, detail=decision.reason)
    try:
        return _service(db).create(user.id, value)
    except (AutomationConflictError, AutomationValidationError) as error:
        _raise(error)


@router.get("", response_model=AutomationList)
def list_automations(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    enabled: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> AutomationList:
    return _service(db).list_owned(user.id, enabled=enabled, limit=limit, offset=offset)


@router.get("/runs", response_model=AutomationRunList)
def list_runs(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    automation_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> AutomationRunList:
    try:
        return _service(db).list_runs(
            user.id,
            automation_id=automation_id,
            limit=limit,
            offset=offset,
        )
    except AutomationNotFoundError as error:
        _raise(error)


@router.get("/runs/{run_id}", response_model=AutomationRunRead)
def get_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRunRead:
    try:
        return _service(db).get_run(user.id, run_id)
    except AutomationNotFoundError as error:
        _raise(error)


@router.post("/runs/{run_id}/recover", response_model=AutomationRunRead)
def recover_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRunRead:
    _require_editor(db, user)
    try:
        return _service(db).recover_failed_run(user.id, run_id)
    except (AutomationNotFoundError, AutomationConflictError, AutomationValidationError) as error:
        _raise(error)


@router.get("/{automation_id}", response_model=AutomationRead)
def get_automation(
    automation_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRead:
    try:
        return _service(db).get_owned(user.id, automation_id)
    except AutomationNotFoundError as error:
        _raise(error)


@router.patch("/{automation_id}", response_model=AutomationRead)
def update_automation(
    automation_id: UUID,
    value: AutomationUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRead:
    _require_editor(db, user)
    try:
        return _service(db).update(user.id, automation_id, value)
    except (AutomationNotFoundError, AutomationConflictError, AutomationValidationError) as error:
        _raise(error)


@router.post("/{automation_id}/pause", response_model=AutomationRead)
def pause_automation(
    automation_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRead:
    _require_editor(db, user)
    try:
        return _service(db).set_enabled(user.id, automation_id, False)
    except AutomationNotFoundError as error:
        _raise(error)


@router.post("/{automation_id}/resume", response_model=AutomationRead)
def resume_automation(
    automation_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRead:
    _require_editor(db, user)
    try:
        return _service(db).set_enabled(user.id, automation_id, True)
    except AutomationNotFoundError as error:
        _raise(error)


@router.post("/{automation_id}/trigger", response_model=AutomationRunRead)
def trigger_automation(
    automation_id: UUID,
    value: AutomationTrigger,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AutomationRunRead:
    _require_editor(db, user)
    try:
        return _service(db).trigger_owned(user.id, automation_id, value)
    except (AutomationNotFoundError, AutomationConflictError, AutomationValidationError) as error:
        _raise(error)
