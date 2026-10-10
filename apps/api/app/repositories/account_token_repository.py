from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.account_token import AccountToken


class AccountTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, token: AccountToken) -> None:
        self.session.add(token)

    def get_by_hash_for_update(self, token_hash: str, purpose: str) -> AccountToken | None:
        return self.session.scalar(
            select(AccountToken)
            .where(AccountToken.token_hash == token_hash, AccountToken.purpose == purpose)
            .with_for_update()
        )

    def latest_for_user(self, user_id: UUID, purpose: str) -> AccountToken | None:
        return self.session.scalar(
            select(AccountToken)
            .where(AccountToken.user_id == user_id, AccountToken.purpose == purpose)
            .order_by(AccountToken.created_at.desc(), AccountToken.id.desc())
            .limit(1)
        )

    def consume_active(self, user_id: UUID, purpose: str, consumed_at: datetime) -> int:
        result = self.session.execute(
            update(AccountToken)
            .where(
                AccountToken.user_id == user_id,
                AccountToken.purpose == purpose,
                AccountToken.consumed_at.is_(None),
            )
            .values(consumed_at=consumed_at)
        )
        return result.rowcount or 0
