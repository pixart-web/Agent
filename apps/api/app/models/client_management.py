from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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


class CrmClient(Base):
    __tablename__ = "crm_clients"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_crm_client_owner_organization"),
        CheckConstraint(
            "lifecycle_status IN ('prospect', 'active', 'paused', 'former', 'archived')",
            name="ck_crm_client_lifecycle_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="prospect", index=True
    )
    industry: Mapped[str | None] = mapped_column(String(128))
    summary: Mapped[str | None] = mapped_column(Text)
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


class CrmProject(Base):
    __tablename__ = "crm_projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'active', 'blocked', 'completed', 'cancelled')",
            name="ck_crm_project_status",
        ),
        Index("ix_crm_projects_owner_client_status", "user_id", "client_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned", index=True)
    starts_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
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


class CrmPipeline(Base):
    __tablename__ = "crm_pipelines"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_crm_pipeline_owner_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class CrmPipelineStage(Base):
    __tablename__ = "crm_pipeline_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "position", name="uq_crm_pipeline_stage_position"),
        UniqueConstraint("pipeline_id", "name", name="uq_crm_pipeline_stage_name"),
        CheckConstraint(
            "default_probability >= 0 AND default_probability <= 100",
            name="ck_crm_pipeline_stage_probability",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    default_probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CrmOpportunity(Base):
    __tablename__ = "crm_opportunities"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'won', 'lost', 'cancelled')",
            name="ck_crm_opportunity_status",
        ),
        CheckConstraint(
            "probability >= 0 AND probability <= 100",
            name="ck_crm_opportunity_probability",
        ),
        CheckConstraint("amount_minor >= 0", name="ck_crm_opportunity_amount"),
        Index(
            "ix_crm_opportunities_owner_client_status",
            "user_id",
            "client_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="SET NULL"), index=True
    )
    pipeline_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stage_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_pipeline_stages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    expected_close_on: Mapped[date | None] = mapped_column(Date)
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


class CrmTaskLink(Base):
    __tablename__ = "crm_task_links"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_crm_task_link_owner_task"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_projects.id", ondelete="SET NULL"), index=True
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class CrmRecordHistory(Base):
    __tablename__ = "crm_record_history"
    __table_args__ = (
        Index(
            "ix_crm_record_history_owner_entity",
            "user_id",
            "entity_type",
            "entity_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    changes: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    actor_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
