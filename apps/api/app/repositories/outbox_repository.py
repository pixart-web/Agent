from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.outbox_event import OutboxEvent
from app.models.workflow_enums import OutboxStatus


class OutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: OutboxEvent) -> None:
        self.session.add(event)

    def get_for_update(self, event_id: UUID) -> OutboxEvent | None:
        return self.session.scalar(
            select(OutboxEvent).where(OutboxEvent.id == event_id).with_for_update(of=OutboxEvent)
        )

    def claim_batch(self, now: datetime, limit: int) -> list[OutboxEvent]:
        statement = (
            select(OutboxEvent)
            .where(
                or_(
                    OutboxEvent.status == OutboxStatus.PENDING,
                    and_(
                        OutboxEvent.status == OutboxStatus.FAILED,
                        OutboxEvent.next_attempt_at.is_not(None),
                        OutboxEvent.next_attempt_at <= now,
                    ),
                ),
            )
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(limit)
            .with_for_update(of=OutboxEvent, skip_locked=True)
        )
        return list(self.session.scalars(statement))
