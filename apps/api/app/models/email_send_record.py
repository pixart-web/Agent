from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.models.workflow_enums import EmailSendStatus


class EmailSendRecord(Base):
    __tablename__ = "email_send_records"
    __table_args__ = (
        UniqueConstraint("task_action_id", name="uq_email_send_action"),
        UniqueConstraint("idempotency_key", name="uq_email_send_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("integration_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_action_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_actions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_executions.id", ondelete="SET NULL"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[EmailSendStatus] = mapped_column(
        String(32), nullable=False, default=EmailSendStatus.PENDING, index=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    thread_id: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )
