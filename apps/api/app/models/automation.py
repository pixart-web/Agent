from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base

TRIGGER_TYPES = (
    "schedule",
    "email_received",
    "calendar_event",
    "crm_change",
    "task_state",
    "manual",
    "webhook",
)
RUN_STATUSES = ("running", "completed", "skipped", "failed")


class Automation(Base):
    __tablename__ = "automations"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('schedule', 'email_received', 'calendar_event', "
            "'crm_change', 'task_state', 'manual', 'webhook')",
            name="ck_automations_trigger_type",
        ),
        CheckConstraint("max_depth BETWEEN 0 AND 10", name="ck_automations_max_depth"),
        CheckConstraint(
            "max_runs_per_window BETWEEN 1 AND 1000",
            name="ck_automations_run_budget",
        ),
        CheckConstraint("window_seconds BETWEEN 60 AND 86400", name="ck_automations_window"),
        CheckConstraint("cooldown_seconds BETWEEN 0 AND 86400", name="ck_automations_cooldown"),
        UniqueConstraint("user_id", "name", name="uq_automations_owner_name"),
        Index("ix_automations_owner_trigger_enabled", "user_id", "trigger_type", "enabled"),
        Index("ix_automations_schedule_due", "trigger_type", "enabled", "next_run_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trigger_config: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    conditions: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    command_template: Mapped[str] = mapped_column(Text, nullable=False)
    max_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    max_runs_per_window: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20, server_default="20"
    )
    window_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3600, server_default="3600"
    )
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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


class AutomationRun(Base):
    __tablename__ = "automation_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('schedule', 'email_received', 'calendar_event', "
            "'crm_change', 'task_state', 'manual', 'webhook')",
            name="ck_automation_runs_trigger_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'skipped', 'failed')",
            name="ck_automation_runs_status",
        ),
        CheckConstraint("depth BETWEEN 0 AND 10", name="ck_automation_runs_depth"),
        UniqueConstraint("automation_id", "dedupe_key", name="uq_automation_runs_dedupe"),
        UniqueConstraint("command_id", name="uq_automation_runs_command"),
        Index("ix_automation_runs_owner_created", "user_id", "created_at"),
        Index("ix_automation_runs_automation_status", "automation_id", "status"),
        Index("ix_automation_runs_correlation", "correlation_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    automation_id: Mapped[UUID] = mapped_column(
        ForeignKey("automations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_key: Mapped[str] = mapped_column(String(255), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    correlation_id: Mapped[UUID] = mapped_column(nullable=False, default=uuid4)
    causation_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("automation_runs.id", ondelete="SET NULL"), index=True
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    command_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("commands.id", ondelete="SET NULL"), index=True
    )
    skipped_reason: Mapped[str | None] = mapped_column(String(128))
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
