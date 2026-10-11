from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.knowledge import Workspace, WorkspaceInvitation, WorkspaceMember
from app.models.transactional_email import TransactionalEmailOutbox
from app.models.user import User
from app.security.account_tokens import (
    encrypt_email_payload,
    generate_account_token,
    hash_account_token,
)
from app.security.email import normalize_email
from app.workspaces.errors import (
    WorkspaceConflictError,
    WorkspaceInvitationError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
)
from app.workspaces.schemas import (
    InvitationCreate,
    InvitationList,
    InvitationRead,
    MemberRoleUpdate,
    MembershipRead,
    OnboardingRead,
    OnboardingUpdate,
    OwnershipTransfer,
    WorkspaceSwitch,
)

MANAGE_ROLES = frozenset({"owner", "admin"})


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()

    def invite(self, actor_id: UUID, workspace_id: UUID, value: InvitationCreate) -> InvitationRead:
        actor = self._membership(workspace_id, actor_id)
        if actor.role not in MANAGE_ROLES:
            raise WorkspacePermissionError("Insufficient workspace permission")
        email = normalize_email(str(value.email))
        existing_user = self.session.scalar(select(User).where(User.email == email))
        if existing_user and self.session.scalar(
            select(WorkspaceMember.id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == existing_user.id,
            )
        ):
            raise WorkspaceConflictError("User is already a workspace member")
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError
        now = utc_now()
        self.session.execute(
            update(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.email == email,
                WorkspaceInvitation.status == "pending",
            )
            .values(status="revoked")
        )
        raw_token = generate_account_token()
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email,
            role=value.role,
            token_hash=hash_account_token(raw_token),
            status="pending",
            invited_by_user_id=actor_id,
            expires_at=now + timedelta(hours=self.settings.workspace_invitation_expire_hours),
        )
        self.session.add(invitation)
        self.session.add(
            TransactionalEmailOutbox(
                recipient=email,
                template="workspace_invitation",
                encrypted_payload=encrypt_email_payload(
                    {"token": raw_token, "full_name": email, "workspace_name": workspace.name},
                    self.settings.auth_secret_key,
                ),
                available_at=now,
            )
        )
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkspaceConflictError("A pending invitation already exists") from error
        self.session.refresh(invitation)
        return self._read_invitation(invitation)

    def list_invitations(self, actor_id: UUID, workspace_id: UUID) -> InvitationList:
        actor = self._membership(workspace_id, actor_id)
        if actor.role not in MANAGE_ROLES:
            raise WorkspacePermissionError("Insufficient workspace permission")
        rows = list(
            self.session.scalars(
                select(WorkspaceInvitation)
                .where(WorkspaceInvitation.workspace_id == workspace_id)
                .order_by(WorkspaceInvitation.created_at.desc())
                .limit(200)
            )
        )
        return InvitationList(invitations=[self._read_invitation(row) for row in rows])

    def revoke_invitation(self, actor_id: UUID, workspace_id: UUID, invitation_id: UUID) -> None:
        actor = self._membership(workspace_id, actor_id)
        if actor.role not in MANAGE_ROLES:
            raise WorkspacePermissionError("Insufficient workspace permission")
        invitation = self.session.scalar(
            select(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.id == invitation_id,
                WorkspaceInvitation.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        if invitation is None:
            raise WorkspaceNotFoundError
        if invitation.status != "pending":
            raise WorkspaceConflictError("Invitation is no longer pending")
        invitation.status = "revoked"
        self.session.commit()

    def accept(self, user: User, raw_token: str) -> MembershipRead:
        invitation = self.session.scalar(
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.token_hash == hash_account_token(raw_token))
            .with_for_update()
        )
        now = utc_now()
        if (
            invitation is None
            or invitation.status != "pending"
            or invitation.expires_at.replace(tzinfo=now.tzinfo) <= now
            or normalize_email(user.email) != invitation.email
        ):
            self.session.rollback()
            raise WorkspaceInvitationError("Invalid or expired invitation")
        member = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=user.id,
            role=invitation.role,
            created_by_user_id=invitation.invited_by_user_id,
        )
        self.session.add(member)
        invitation.status = "accepted"
        invitation.accepted_at = now
        invitation.accepted_by_user_id = user.id
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkspaceConflictError("User is already a workspace member") from error
        self.session.refresh(member)
        return MembershipRead.model_validate(member, from_attributes=True)

    def update_member(
        self,
        actor_id: UUID,
        workspace_id: UUID,
        member_id: UUID,
        value: MemberRoleUpdate,
    ) -> MembershipRead:
        actor = self._membership(workspace_id, actor_id)
        if actor.role not in MANAGE_ROLES:
            raise WorkspacePermissionError("Insufficient workspace permission")
        member = self._member_for_update(workspace_id, member_id)
        if member.role == "owner" or (actor.role == "admin" and member.role == "admin"):
            raise WorkspacePermissionError("Owner authority is required")
        member.role = value.role
        self.session.commit()
        self.session.refresh(member)
        return MembershipRead.model_validate(member, from_attributes=True)

    def remove_member(self, actor_id: UUID, workspace_id: UUID, member_id: UUID) -> None:
        actor = self._membership(workspace_id, actor_id)
        if actor.role not in MANAGE_ROLES:
            raise WorkspacePermissionError("Insufficient workspace permission")
        member = self._member_for_update(workspace_id, member_id)
        if member.role == "owner" or (actor.role == "admin" and member.role == "admin"):
            raise WorkspacePermissionError("Owner authority is required")
        self.session.delete(member)
        self.session.commit()

    def transfer_ownership(
        self,
        actor_id: UUID,
        workspace_id: UUID,
        value: OwnershipTransfer,
    ) -> MembershipRead:
        actor = self._membership(workspace_id, actor_id)
        if actor.role != "owner":
            raise WorkspacePermissionError("Owner authority is required")
        target = self.session.scalar(
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == value.user_id,
            )
            .with_for_update()
        )
        if target is None or target.id == actor.id:
            raise WorkspaceConflictError("Ownership target must be another member")
        actor.role = "admin"
        target.role = "owner"
        self.session.commit()
        self.session.refresh(target)
        return MembershipRead.model_validate(target, from_attributes=True)

    def switch(self, user: User, value: WorkspaceSwitch) -> None:
        membership = self._membership(value.workspace_id, user.id)
        workspace = self.session.get(Workspace, membership.workspace_id)
        if workspace is None or workspace.status != "active":
            raise WorkspaceNotFoundError
        user.active_workspace_id = workspace.id
        self.session.commit()

    def onboarding(self, user: User) -> OnboardingRead:
        workspace = self._active_workspace(user)
        return self._onboarding_read(user, workspace)

    def update_onboarding(self, user: User, value: OnboardingUpdate) -> OnboardingRead:
        workspace = self._active_workspace(user)
        membership = self._membership(workspace.id, user.id)
        if membership.role not in MANAGE_ROLES and (
            value.company_name is not None
            or value.company_description is not None
            or value.primary_objectives is not None
        ):
            raise WorkspacePermissionError("Insufficient workspace permission")
        if value.company_name is not None:
            workspace.name = value.company_name
        if value.company_description is not None:
            workspace.description = value.company_description
        if value.primary_objectives is not None:
            workspace.primary_objectives = value.primary_objectives
        user.onboarding_step = max(user.onboarding_step, value.step)
        if value.complete:
            if not workspace.description or not workspace.primary_objectives:
                raise WorkspaceConflictError(
                    "Company description and at least one objective are required"
                )
            user.onboarding_step = 8
            user.onboarding_completed_at = user.onboarding_completed_at or utc_now()
        self.session.commit()
        self.session.refresh(user)
        self.session.refresh(workspace)
        return self._onboarding_read(user, workspace)

    def _active_workspace(self, user: User) -> Workspace:
        if user.active_workspace_id is None:
            raise WorkspaceNotFoundError
        self._membership(user.active_workspace_id, user.id)
        workspace = self.session.get(Workspace, user.active_workspace_id)
        if workspace is None or workspace.status != "active":
            raise WorkspaceNotFoundError
        return workspace

    def _membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember:
        member = self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if member is None:
            raise WorkspaceNotFoundError
        return member

    def _member_for_update(self, workspace_id: UUID, member_id: UUID) -> WorkspaceMember:
        member = self.session.scalar(
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.id == member_id,
            )
            .with_for_update()
        )
        if member is None:
            raise WorkspaceNotFoundError
        return member

    @staticmethod
    def _read_invitation(item: WorkspaceInvitation) -> InvitationRead:
        return InvitationRead.model_validate(item, from_attributes=True)

    @staticmethod
    def _onboarding_read(user: User, workspace: Workspace) -> OnboardingRead:
        return OnboardingRead(
            step=user.onboarding_step,
            completed_at=user.onboarding_completed_at,
            workspace_id=workspace.id,
            company_name=workspace.name,
            company_description=workspace.description,
            primary_objectives=workspace.primary_objectives,
        )
