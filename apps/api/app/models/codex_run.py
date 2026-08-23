from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.models.workflow_enums import CodexRunStatus


class CodexRun(Base):
    __tablename__ = "codex_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_action_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_actions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repository: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    base_branch: Mapped[str] = mapped_column(String(200), nullable=False)
    working_branch: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[CodexRunStatus] = mapped_column(
        Enum(
            CodexRunStatus,
            name="codex_run_status",
            native_enum=False,
            length=32,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=CodexRunStatus.CREATED,
        server_default=CodexRunStatus.CREATED.value,
        index=True,
    )
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    runner_type: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(String(500))
    files_changed: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tests_run: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tests_passed: Mapped[bool | None] = mapped_column(Boolean)
    commit_sha: Mapped[str | None] = mapped_column(String(40))
    pull_request_number: Mapped[int | None] = mapped_column(Integer)
    pull_request_url: Mapped[str | None] = mapped_column(String(500))
    correlation_id: Mapped[UUID] = mapped_column(nullable=False, default=uuid4, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )
