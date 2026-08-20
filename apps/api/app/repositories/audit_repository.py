from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.command import Command


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, log: AuditLog) -> None:
        self.session.add(log)

    def list_for_correlation_owned(
        self, correlation_id: UUID, user_id: UUID, limit: int = 200
    ) -> list[AuditLog]:
        owned = self.session.scalar(
            select(Command.id).where(
                Command.correlation_id == correlation_id, Command.user_id == user_id
            )
        )
        if owned is None:
            return []
        return list(
            self.session.scalars(
                select(AuditLog)
                .where(AuditLog.correlation_id == correlation_id)
                .order_by(AuditLog.created_at, AuditLog.id)
                .limit(limit)
            )
        )
