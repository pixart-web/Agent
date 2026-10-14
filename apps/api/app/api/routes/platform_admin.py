from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_superuser
from app.api.dependencies.origin import require_allowed_origin
from app.db.session import get_db
from app.models.user import User
from app.platform_admin.schemas import (
    PlatformOverview,
    PlatformUser,
    PlatformUserList,
    PlatformWorkspace,
    PlatformWorkspaceList,
    UserStatusUpdate,
    WorkspaceStatusUpdate,
)
from app.platform_admin.service import PlatformAdminService

router = APIRouter(prefix="/platform-admin", tags=["platform-admin"])


@router.get("/overview", response_model=PlatformOverview)
def overview(
    _user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformOverview:
    return PlatformAdminService(db).overview()


@router.get("/workspaces", response_model=PlatformWorkspaceList)
def workspaces(
    _user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformWorkspaceList:
    return PlatformAdminService(db).list_workspaces()


@router.patch(
    "/workspaces/{workspace_id}",
    response_model=PlatformWorkspace,
    dependencies=[Depends(require_allowed_origin)],
)
def update_workspace(
    workspace_id: UUID,
    value: WorkspaceStatusUpdate,
    user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformWorkspace:
    try:
        return PlatformAdminService(db).update_workspace_status(workspace_id, value.status, user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Workspace not found") from error


@router.get("/users", response_model=PlatformUserList)
def users(
    _user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformUserList:
    return PlatformAdminService(db).list_users()


@router.patch(
    "/users/{user_id}",
    response_model=PlatformUser,
    dependencies=[Depends(require_allowed_origin)],
)
def update_user(
    user_id: UUID,
    value: UserStatusUpdate,
    user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformUser:
    try:
        return PlatformAdminService(db).update_user_status(user_id, value.is_active, user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="User not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
