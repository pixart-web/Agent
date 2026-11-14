from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.user import User


class IntegrationOAuthStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, value: IntegrationOAuthState) -> IntegrationOAuthState:
        self.session.add(value)
        return value

    def consume(
        self,
        state_id: UUID,
        user_id: UUID,
        provider: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None:
        value = self.session.scalar(
            select(IntegrationOAuthState)
            .where(
                IntegrationOAuthState.id == state_id,
                IntegrationOAuthState.user_id == user_id,
                IntegrationOAuthState.provider == provider,
                IntegrationOAuthState.purpose == purpose,
                IntegrationOAuthState.expires_at > now,
                IntegrationOAuthState.consumed_at.is_(None),
            )
            .with_for_update()
        )
        if value is None:
            return None
        value.consumed_at = now
        if value.workspace_id is not None:
            return value.workspace_id
        return (
            self.session.scalar(select(User.active_workspace_id).where(User.id == value.user_id))
            or value.user_id
        )

    def cleanup(self, now: datetime, consumed_before: datetime) -> int:
        result = self.session.execute(
            delete(IntegrationOAuthState).where(
                (IntegrationOAuthState.expires_at <= now)
                | (
                    IntegrationOAuthState.consumed_at.is_not(None)
                    & (IntegrationOAuthState.consumed_at <= consumed_before)
                )
            )
        )
        return result.rowcount or 0
