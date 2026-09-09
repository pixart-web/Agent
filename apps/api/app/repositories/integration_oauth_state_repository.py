from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.models.integration_oauth_state import IntegrationOAuthState


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
    ) -> bool:
        result = self.session.execute(
            update(IntegrationOAuthState)
            .where(
                IntegrationOAuthState.id == state_id,
                IntegrationOAuthState.user_id == user_id,
                IntegrationOAuthState.provider == provider,
                IntegrationOAuthState.purpose == purpose,
                IntegrationOAuthState.expires_at > now,
                IntegrationOAuthState.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        return result.rowcount == 1

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
