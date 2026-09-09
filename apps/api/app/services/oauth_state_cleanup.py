from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.repositories.integration_oauth_state_repository import (
    IntegrationOAuthStateRepository,
)


def cleanup_oauth_states(session: Session, retention_days: int = 7) -> int:
    now = utc_now()
    deleted = IntegrationOAuthStateRepository(session).cleanup(
        now=now,
        consumed_before=now - timedelta(days=retention_days),
    )
    session.commit()
    return deleted
