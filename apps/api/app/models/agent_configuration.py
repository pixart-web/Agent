from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class AgentConfiguration(Base):
    __tablename__ = "agent_configurations"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "agent_id", name="uq_agent_configurations_workspace_agent"
        ),
        CheckConstraint(
            "approval_policy IN ('platform_default', 'always', 'risk_based')",
            name="ck_agent_configurations_approval_policy",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    model: Mapped[str | None] = mapped_column(String(128))
    allowed_tools: Mapped[list[str] | None] = mapped_column(JSON)
    approval_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="platform_default", server_default="platform_default"
    )
    max_actions_per_task: Mapped[int | None] = mapped_column(Integer)
    monthly_token_budget: Mapped[int | None] = mapped_column(Integer)
    knowledge_source_ids: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    updated_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
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
