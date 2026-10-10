from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.integration_account import IntegrationAccount
from app.workspaces.scope import active_workspace_id


class IntegrationAccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, value: IntegrationAccount) -> IntegrationAccount:
        self.session.add(value)
        return value

    def get_owned(
        self, account_id: UUID, user_id: UUID, provider: str | None = None
    ) -> IntegrationAccount | None:
        conditions = [
            IntegrationAccount.id == account_id,
            self._scope(user_id),
        ]
        if provider is not None:
            conditions.append(IntegrationAccount.provider == provider)
        return self.session.scalar(select(IntegrationAccount).where(*conditions))

    def get_by_external(
        self, user_id: UUID, provider: str, external_id: str
    ) -> IntegrationAccount | None:
        return self.session.scalar(
            select(IntegrationAccount).where(
                self._scope(user_id),
                IntegrationAccount.provider == provider,
                IntegrationAccount.external_account_id == external_id,
            )
        )

    def list_owned(self, user_id: UUID, provider: str | None = None) -> list[IntegrationAccount]:
        conditions = [self._scope(user_id)]
        if provider is not None:
            conditions.append(IntegrationAccount.provider == provider)
        return list(
            self.session.scalars(
                select(IntegrationAccount)
                .where(*conditions)
                .order_by(IntegrationAccount.email_address)
            )
        )

    @staticmethod
    def _scope(user_id: UUID):
        return or_(
            IntegrationAccount.workspace_id == active_workspace_id(user_id),
            (IntegrationAccount.workspace_id.is_(None) & (IntegrationAccount.user_id == user_id)),
        )
