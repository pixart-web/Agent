from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

WorkspaceRole = Literal["owner", "admin", "manager", "member", "viewer"]
InvitableRole = Literal["admin", "manager", "member", "viewer"]


class StrictWorkspaceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvitationCreate(StrictWorkspaceModel):
    email: EmailStr
    role: InvitableRole = "member"


class InvitationAccept(StrictWorkspaceModel):
    token: str = Field(min_length=32, max_length=512)


class MemberRoleUpdate(StrictWorkspaceModel):
    role: InvitableRole


class OwnershipTransfer(StrictWorkspaceModel):
    user_id: UUID


class WorkspaceSwitch(StrictWorkspaceModel):
    workspace_id: UUID


class OnboardingUpdate(StrictWorkspaceModel):
    step: int = Field(ge=0, le=8)
    company_name: str | None = Field(default=None, min_length=2, max_length=200)
    company_description: str | None = Field(default=None, max_length=2000)
    primary_objectives: list[str] | None = Field(default=None, max_length=6)
    complete: bool = False

    @field_validator("company_name", "company_description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("primary_objectives")
    @classmethod
    def normalize_objectives(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [" ".join(item.split()) for item in value]
        if any(not item or len(item) > 120 for item in normalized):
            raise ValueError("Objectives must contain between 1 and 120 characters")
        return list(dict.fromkeys(normalized))


class OnboardingRead(StrictWorkspaceModel):
    step: int
    completed_at: datetime | None
    workspace_id: UUID
    company_name: str
    company_description: str | None
    primary_objectives: list[str]


class InvitationRead(StrictWorkspaceModel):
    id: UUID
    workspace_id: UUID
    email: EmailStr
    role: InvitableRole
    status: Literal["pending", "accepted", "revoked", "expired"]
    expires_at: datetime
    created_at: datetime


class InvitationList(StrictWorkspaceModel):
    invitations: list[InvitationRead]


class MembershipRead(StrictWorkspaceModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    created_at: datetime


class WorkspaceMemberDetail(StrictWorkspaceModel):
    id: UUID
    user_id: UUID
    email: EmailStr
    full_name: str
    role: WorkspaceRole
    created_at: datetime


class WorkspaceSettingsRead(StrictWorkspaceModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    sector: str | None
    country: str | None
    website: str | None
    branding: dict[str, object]
    retention_days: int
    ai_monthly_token_limit: int | None
    is_synthetic_demo: bool
    role: WorkspaceRole
    members: list[WorkspaceMemberDetail]


class WorkspaceSettingsUpdate(StrictWorkspaceModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    sector: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    website: str | None = Field(default=None, max_length=2048, pattern=r"^https?://")
    branding: dict[str, object] = Field(default_factory=dict)
    retention_days: int = Field(ge=30, le=3650)
    ai_monthly_token_limit: int | None = Field(default=None, ge=1000, le=1_000_000_000)
