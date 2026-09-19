from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CrmOrganization(Base):
    __tablename__ = "crm_organizations"
    __table_args__ = (Index("ix_crm_organizations_owner_name", "user_id", "normalized_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
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


class CrmContact(Base):
    __tablename__ = "crm_contacts"
    __table_args__ = (Index("ix_crm_contacts_owner_name", "user_id", "normalized_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="SET NULL"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
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


class CrmContactMethod(Base):
    __tablename__ = "crm_contact_methods"
    __table_args__ = (
        UniqueConstraint(
            "contact_id", "method_type", "normalized_value", name="uq_crm_contact_method"
        ),
        CheckConstraint("method_type IN ('email', 'phone')", name="ck_crm_contact_method_type"),
        Index(
            "ix_crm_contact_methods_owner_identity",
            "user_id",
            "method_type",
            "normalized_value",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(320), nullable=False)
    label: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class CrmOrganizationMember(Base):
    __tablename__ = "crm_organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "contact_id", name="uq_crm_organization_member"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class CrmAddress(Base):
    __tablename__ = "crm_addresses"
    __table_args__ = (
        CheckConstraint(
            "(contact_id IS NOT NULL) <> (organization_id IS NOT NULL)",
            name="ck_crm_address_one_owner",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="business")
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class CrmTag(Base):
    __tablename__ = "crm_tags"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", name="uq_crm_tag_owner_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class CrmContactTag(Base):
    __tablename__ = "crm_contact_tags"
    __table_args__ = (UniqueConstraint("contact_id", "tag_id", name="uq_crm_contact_tag"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_tags.id", ondelete="CASCADE"), nullable=False, index=True
    )


class CrmOrganizationTag(Base):
    __tablename__ = "crm_organization_tags"
    __table_args__ = (
        UniqueConstraint("organization_id", "tag_id", name="uq_crm_organization_tag"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("crm_tags.id", ondelete="CASCADE"), nullable=False, index=True
    )


class CrmNote(Base):
    __tablename__ = "crm_notes"
    __table_args__ = (
        CheckConstraint(
            "(contact_id IS NOT NULL) <> (organization_id IS NOT NULL)",
            name="ck_crm_note_one_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )


class CrmActivity(Base):
    __tablename__ = "crm_activities"
    __table_args__ = (
        CheckConstraint(
            "contact_id IS NOT NULL OR organization_id IS NOT NULL",
            name="ck_crm_activity_has_target",
        ),
        UniqueConstraint("contact_id", "email_reference_id", name="uq_crm_activity_contact_email"),
        UniqueConstraint(
            "contact_id", "calendar_reference_id", name="uq_crm_activity_contact_calendar"
        ),
        UniqueConstraint("organization_id", "email_reference_id", name="uq_crm_activity_org_email"),
        UniqueConstraint(
            "organization_id", "calendar_reference_id", name="uq_crm_activity_org_calendar"
        ),
        Index("ix_crm_activities_owner_occurred", "user_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_contacts.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("crm_organizations.id", ondelete="CASCADE"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    email_reference_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_references.id", ondelete="SET NULL"), index=True
    )
    calendar_reference_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("calendar_references.id", ondelete="SET NULL"), index=True
    )
    created_by_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_actions.id", ondelete="SET NULL"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
