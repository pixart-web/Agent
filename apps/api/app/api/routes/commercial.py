from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.origin import require_allowed_origin
from app.commercial.schemas import EntitlementDecision, PlanRead, SubscriptionRead
from app.commercial.service import CommercialService
from app.db.session import get_db
from app.models.knowledge import WorkspaceMember
from app.models.user import User

router = APIRouter(prefix="/commercial", tags=["commercial"])


def _workspace(user: User) -> UUID:
    if user.active_workspace_id is None:
        raise HTTPException(status_code=409, detail="An active workspace is required")
    return user.active_workspace_id


def _require_owner(db: Session, user: User) -> None:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None or membership.role != "owner":
        raise HTTPException(status_code=403, detail="Workspace owner permission is required")


@router.get("/plans", response_model=list[PlanRead])
def plans(
    _user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PlanRead]:
    return CommercialService(db).list_plans()


@router.get("/subscription", response_model=SubscriptionRead)
def subscription(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionRead:
    try:
        return CommercialService(db).subscription(_workspace(user))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/entitlements/{name}", response_model=EntitlementDecision)
def entitlement(
    name: str,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EntitlementDecision:
    try:
        return CommercialService(db).entitlement(_workspace(user), name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/subscription/cancel",
    response_model=SubscriptionRead,
    dependencies=[Depends(require_allowed_origin)],
)
def cancel_subscription(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionRead:
    _require_owner(db, user)
    try:
        return CommercialService(db).cancel(_workspace(user))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
