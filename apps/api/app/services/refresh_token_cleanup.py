from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.repositories.refresh_token_repository import RefreshTokenRepository


def cleanup_refresh_tokens(session: Session, retention_days: int) -> int:
    now = utc_now()
    deleted = RefreshTokenRepository(session).delete_expired_or_old_revoked(
        now=now,
        revoked_before=now - timedelta(days=retention_days),
    )
    session.commit()
    return deleted
