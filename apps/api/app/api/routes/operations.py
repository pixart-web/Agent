from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.operations.schemas import OperationsAnalytics, OperationsOverview
from app.operations.service import OperationsService

router = APIRouter(prefix="/operations", tags=["operations"])


def _workspace(user: User) -> UUID:
    if user.active_workspace_id is None:
        raise HTTPException(status_code=409, detail="An active workspace is required")
    return user.active_workspace_id


@router.get("/overview", response_model=OperationsOverview)
def get_overview(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OperationsOverview:
    return OperationsService(db).overview(_workspace(user), user.id)


@router.get("/analytics", response_model=OperationsAnalytics)
def get_analytics(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> OperationsAnalytics:
    return OperationsService(db).analytics(_workspace(user), days)
