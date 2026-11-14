from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.origin import require_allowed_origin
from app.db.session import get_db
from app.models.user import User
from app.notifications.schemas import (
    NotificationList,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from app.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _workspace(user: User) -> UUID:
    if user.active_workspace_id is None:
        raise HTTPException(status_code=409, detail="An active workspace is required")
    return user.active_workspace_id


@router.get("", response_model=NotificationList)
def list_notifications(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    unread_only: bool = False,
) -> NotificationList:
    return NotificationService(db).list(user.id, _workspace(user), unread_only=unread_only)


@router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def mark_notification_read(
    notification_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        NotificationService(db).mark_read(user.id, _workspace(user), notification_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Notification not found") from error
    return Response(status_code=204)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def mark_all_notifications_read(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    NotificationService(db).mark_all_read(user.id, _workspace(user))
    return Response(status_code=204)


@router.get("/preferences", response_model=NotificationPreferenceRead)
def get_preferences(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationPreferenceRead:
    return NotificationService(db).preferences(user.id)


@router.put(
    "/preferences",
    response_model=NotificationPreferenceRead,
    dependencies=[Depends(require_allowed_origin)],
)
def update_preferences(
    value: NotificationPreferenceUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationPreferenceRead:
    return NotificationService(db).update_preferences(user.id, value)
