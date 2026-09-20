from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('idea', 'active', 'paused', 'completed', 'archived')",
            name="ck_marketing_campaign_status",
        ),
        Index("ix_marketing_campaigns_owner_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_clients.id", ondelete="SET NULL"), index=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="idea", index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
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


class MarketingContent(Base):
    __tablename__ = "marketing_content"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN "
            "('idea', 'draft', 'review', 'approved', 'scheduled', 'published', 'archived')",
            name="ck_marketing_content_lifecycle",
        ),
        Index(
            "ix_marketing_content_owner_campaign_status",
            "user_id",
            "campaign_id",
            "lifecycle_status",
        ),
        Index("ix_marketing_content_owner_schedule", "user_id", "scheduled_for"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="idea", index=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
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


class MarketingAsset(Base):
    __tablename__ = "marketing_assets"
    __table_args__ = (
        CheckConstraint(
            "(campaign_id IS NOT NULL) OR (content_id IS NOT NULL)",
            name="ck_marketing_asset_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), index=True
    )
    content_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("marketing_content.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    locator: Mapped[str] = mapped_column(String(2048), nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class MarketingPublication(Base):
    __tablename__ = "marketing_publications"
    __table_args__ = (
        UniqueConstraint(
            "content_id", "external_reference", name="uq_marketing_publication_reference"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("marketing_content.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(2048), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class MarketingPerformanceMetric(Base):
    __tablename__ = "marketing_performance_metrics"
    __table_args__ = (
        CheckConstraint(
            "(campaign_id IS NOT NULL) OR (content_id IS NOT NULL)",
            name="ck_marketing_metric_target",
        ),
        Index(
            "ix_marketing_metrics_owner_name_measured",
            "user_id",
            "metric_name",
            "measured_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), index=True
    )
    content_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("marketing_content.id", ondelete="CASCADE"), index=True
    )
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class MarketingContentHistory(Base):
    __tablename__ = "marketing_content_history"
    __table_args__ = (
        Index(
            "ix_marketing_content_history_owner_content",
            "user_id",
            "content_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("marketing_content.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    actor_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
