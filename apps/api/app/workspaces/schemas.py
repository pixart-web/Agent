from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

WorkspaceRole = Literal["owner", "admin", "manager", "member", "viewer"]
InvitableRole = Literal["admin", "manager", "member", "viewer"]


class StrictWorkspaceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvitationCreate(StrictWorkspaceModel):
    email: EmailStr
    role: InvitableRole = "member"


class InvitationAccept(StrictWorkspaceModel):
    token: str = Field(min_length=32, max_length=512)


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
