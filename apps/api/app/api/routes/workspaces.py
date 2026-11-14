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
    MemberRoleUpdate,
    MembershipRead,
    OnboardingRead,
    OnboardingUpdate,
    OwnershipTransfer,
    WorkspaceSettingsRead,
    WorkspaceSettingsUpdate,
    WorkspaceSwitch,
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


@router.get("/onboarding", response_model=OnboardingRead)
def onboarding(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingRead:
    try:
        return WorkspaceService(db).onboarding(user)
    except WorkspaceNotFoundError as error:
        _raise(error)


@router.get("/settings", response_model=WorkspaceSettingsRead)
def workspace_settings(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceSettingsRead:
    try:
        return WorkspaceService(db).get_workspace_settings(user)
    except WorkspaceNotFoundError as error:
        _raise(error)


@router.put(
    "/settings",
    response_model=WorkspaceSettingsRead,
    dependencies=[Depends(require_allowed_origin)],
)
def update_workspace_settings(
    value: WorkspaceSettingsUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkspaceSettingsRead:
    try:
        return WorkspaceService(db).update_settings(user, value)
    except (WorkspaceNotFoundError, WorkspacePermissionError) as error:
        _raise(error)


@router.patch(
    "/onboarding",
    response_model=OnboardingRead,
    dependencies=[Depends(require_allowed_origin)],
)
def update_onboarding(
    value: OnboardingUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingRead:
    try:
        return WorkspaceService(db).update_onboarding(user, value)
    except (WorkspaceNotFoundError, WorkspacePermissionError, WorkspaceConflictError) as error:
        _raise(error)


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


@router.patch(
    "/{workspace_id}/members/{member_id}",
    response_model=MembershipRead,
    dependencies=[Depends(require_allowed_origin)],
)
def update_member(
    workspace_id: UUID,
    member_id: UUID,
    value: MemberRoleUpdate,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MembershipRead:
    try:
        return WorkspaceService(db).update_member(user.id, workspace_id, member_id, value)
    except (WorkspaceNotFoundError, WorkspacePermissionError) as error:
        _raise(error)


@router.delete(
    "/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def remove_member(
    workspace_id: UUID,
    member_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        WorkspaceService(db).remove_member(user.id, workspace_id, member_id)
    except (WorkspaceNotFoundError, WorkspacePermissionError) as error:
        _raise(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{workspace_id}/ownership-transfer",
    response_model=MembershipRead,
    dependencies=[Depends(require_allowed_origin)],
)
def transfer_ownership(
    workspace_id: UUID,
    value: OwnershipTransfer,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MembershipRead:
    try:
        return WorkspaceService(db).transfer_ownership(user.id, workspace_id, value)
    except (WorkspaceNotFoundError, WorkspacePermissionError, WorkspaceConflictError) as error:
        _raise(error)


@router.post(
    "/switch",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_allowed_origin)],
)
def switch_workspace(
    value: WorkspaceSwitch,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    try:
        WorkspaceService(db).switch(user, value)
    except WorkspaceNotFoundError as error:
        _raise(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
