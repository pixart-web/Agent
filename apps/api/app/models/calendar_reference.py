from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CalendarReference(Base):
    __tablename__ = "calendar_references"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "calendar_id", "event_id", name="uq_calendar_reference_event"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("integration_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    command_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("commands.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
