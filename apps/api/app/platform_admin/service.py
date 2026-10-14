from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.audit_log import AuditLog
from app.models.integration_account import IntegrationAccount
from app.models.knowledge import Workspace, WorkspaceMember
from app.models.refresh_token import RefreshToken
from app.models.transactional_email import TransactionalEmailOutbox
from app.models.user import User
from app.models.workflow_enums import ActorType
from app.platform_admin.schemas import (
    PlatformOverview,
    PlatformUser,
    PlatformUserList,
    PlatformWorkspace,
    PlatformWorkspaceList,
    ProviderStatus,
)


class PlatformAdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def overview(self) -> PlatformOverview:
        settings = get_settings()
        return PlatformOverview(
            workspace_count=self._count(Workspace.id),
            active_workspace_count=self._count(Workspace.id, Workspace.status == "active"),
            user_count=self._count(User.id),
            active_user_count=self._count(User.id, User.is_active.is_(True)),
            active_session_count=self._count(
                RefreshToken.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > utc_now(),
            ),
            integration_account_count=self._count(IntegrationAccount.id),
            failed_email_count=self._count(
                TransactionalEmailOutbox.id, TransactionalEmailOutbox.status == "failed"
            ),
            providers=[
                ProviderStatus(
                    provider="openai",
                    enabled=settings.ai_provider == "openai",
                    configured=bool(settings.openai_api_key),
                ),
                ProviderStatus(
                    provider="github",
                    enabled=settings.github_integration_enabled,
                    configured=bool(settings.github_token),
                ),
                ProviderStatus(
                    provider="codex",
                    enabled=settings.codex_integration_enabled,
                    configured=settings.codex_credential_configured,
                ),
                ProviderStatus(
                    provider="google_email",
                    enabled=settings.email_integration_enabled,
                    configured=bool(settings.google_client_id and settings.google_client_secret),
                ),
                ProviderStatus(
                    provider="google_calendar",
                    enabled=settings.calendar_integration_enabled,
                    configured=bool(settings.google_client_id and settings.google_client_secret),
                ),
            ],
        )

    def list_workspaces(self) -> PlatformWorkspaceList:
        rows = self.db.execute(
            select(Workspace, func.count(WorkspaceMember.id))
            .outerjoin(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .group_by(Workspace.id)
            .order_by(Workspace.created_at.desc())
            .limit(500)
        ).all()
        return PlatformWorkspaceList(
            workspaces=[
                PlatformWorkspace(
                    id=workspace.id,
                    name=workspace.name,
                    slug=workspace.slug,
                    status=workspace.status,
                    created_at=workspace.created_at,
                    member_count=member_count,
                )
                for workspace, member_count in rows
            ]
        )

    def list_users(self) -> PlatformUserList:
        users = self.db.scalars(select(User).order_by(User.created_at.desc()).limit(500)).all()
        return PlatformUserList(users=[PlatformUser.model_validate(user) for user in users])

    def update_workspace_status(
        self, workspace_id: UUID, new_status: str, actor_id: UUID
    ) -> PlatformWorkspace:
        workspace = self.db.get(Workspace, workspace_id)
        if workspace is None:
            raise LookupError
        previous = workspace.status
        workspace.status = new_status
        self._audit(
            actor_id, "platform.workspace_status_changed", workspace.id, previous, new_status
        )
        self.db.commit()
        member_count = self._count(WorkspaceMember.id, WorkspaceMember.workspace_id == workspace.id)
        return PlatformWorkspace(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,
            status=workspace.status,
            created_at=workspace.created_at,
            member_count=member_count,
        )

    def update_user_status(self, user_id: UUID, active: bool, actor_id: UUID) -> PlatformUser:
        user = self.db.get(User, user_id)
        if user is None:
            raise LookupError
        if user.id == actor_id and not active:
            raise ValueError("A platform administrator cannot deactivate their own account")
        previous = user.is_active
        user.is_active = active
        if not active:
            now = utc_now()
            for token in self.db.scalars(
                select(RefreshToken).where(
                    RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
                )
            ):
                token.revoked_at = now
        self._audit(actor_id, "platform.user_status_changed", user.id, previous, active)
        self.db.commit()
        return PlatformUser.model_validate(user)

    def _count(self, column, *conditions) -> int:
        return self.db.scalar(select(func.count(column)).where(*conditions)) or 0

    def _audit(
        self, actor_id: UUID, event_type: str, resource_id: UUID, previous: object, value: object
    ) -> None:
        self.db.add(
            AuditLog(
                actor_type=ActorType.USER,
                actor_id=actor_id,
                event_type=event_type,
                resource_type="platform_admin",
                resource_id=resource_id,
                metadata_payload={"previous": previous, "value": value},
                correlation_id=uuid4(),
            )
        )
