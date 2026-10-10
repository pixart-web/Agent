from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.api.dependencies.origin import require_allowed_origin
from app.db.session import get_db
from app.models.user import User
from app.workspaces.errors import (
    WorkspaceConflictError,
    WorkspaceInvitationError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
)
from app.workspaces.schemas import (
    InvitationAccept,
    InvitationCreate,
    InvitationList,
    InvitationRead,
    MembershipRead,
)
from app.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _raise(error: Exception) -> None:
    if isinstance(error, WorkspaceNotFoundError):
        raise HTTPException(status_code=404, detail="Resource not found") from error
    if isinstance(error, WorkspacePermissionError):
        raise HTTPException(status_code=403, detail=str(error)) from error
    if isinstance(error, WorkspaceConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, WorkspaceInvitationError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


@router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_allowed_origin)],
)
def invite(
    workspace_id: UUID,
    value: InvitationCreate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationRead:
    try:
        return WorkspaceService(db).invite(user.id, workspace_id, value)
    except (WorkspaceNotFoundError, WorkspacePermissionError, WorkspaceConflictError) as error:
        _raise(error)


@router.get("/{workspace_id}/invitations", response_model=InvitationList)
def invitations(
    workspace_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitationList:
    try:
        return WorkspaceService(db).list_invitations(user.id, workspace_id)
    except (WorkspaceNotFoundError, WorkspacePermissionError) as error:
        _raise(error)


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def revoke_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        WorkspaceService(db).revoke_invitation(user.id, workspace_id, invitation_id)
    except (WorkspaceNotFoundError, WorkspacePermissionError, WorkspaceConflictError) as error:
        _raise(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/invitations/accept",
    response_model=MembershipRead,
    dependencies=[Depends(require_allowed_origin)],
)
def accept_invitation(
    value: InvitationAccept,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MembershipRead:
    try:
        return WorkspaceService(db).accept(user, value.token)
    except (WorkspaceInvitationError, WorkspaceConflictError) as error:
        _raise(error)
