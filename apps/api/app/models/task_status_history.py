from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.models.workflow_enums import TaskStatus


def _task_status_enum() -> Enum:
    return Enum(
        TaskStatus,
        name="task_status",
        native_enum=False,
        length=32,
        values_callable=lambda enum: [item.value for item in enum],
    )


class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[TaskStatus | None] = mapped_column(
        _task_status_enum(),
        nullable=True,
    )
    to_status: Mapped[TaskStatus] = mapped_column(
        _task_status_enum(),
        nullable=False,
    )
    changed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        index=True,
    )
