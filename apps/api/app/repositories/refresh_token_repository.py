from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, token: RefreshToken) -> None:
        self.session.add(token)

    def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        statement = (
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )
        return self.session.scalar(statement)

    def revoke_family(self, family_id: UUID, revoked_at: datetime) -> int:
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = self.session.execute(statement)
        return result.rowcount or 0

    def delete_expired_or_old_revoked(
        self,
        now: datetime,
        revoked_before: datetime,
    ) -> int:
        statement = delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at < now,
                RefreshToken.revoked_at < revoked_before,
            )
        )
        result = self.session.execute(
            statement.execution_options(synchronize_session=False),
        )
        return result.rowcount or 0
