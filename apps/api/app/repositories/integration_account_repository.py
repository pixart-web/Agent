from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration_account import IntegrationAccount


class IntegrationAccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, value: IntegrationAccount) -> IntegrationAccount:
        self.session.add(value)
        return value

    def get_owned(self, account_id: UUID, user_id: UUID) -> IntegrationAccount | None:
        return self.session.scalar(
            select(IntegrationAccount).where(
                IntegrationAccount.id == account_id,
                IntegrationAccount.user_id == user_id,
            )
        )

    def get_by_external(
        self, user_id: UUID, provider: str, external_id: str
    ) -> IntegrationAccount | None:
        return self.session.scalar(
            select(IntegrationAccount).where(
                IntegrationAccount.user_id == user_id,
                IntegrationAccount.provider == provider,
                IntegrationAccount.external_account_id == external_id,
            )
        )

    def list_owned(self, user_id: UUID) -> list[IntegrationAccount]:
        return list(
            self.session.scalars(
                select(IntegrationAccount)
                .where(IntegrationAccount.user_id == user_id)
                .order_by(IntegrationAccount.email_address)
            )
        )
