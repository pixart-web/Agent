from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlatformWorkspace(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    member_count: int


class PlatformUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: datetime | None


class ProviderStatus(BaseModel):
    provider: str
    enabled: bool
    configured: bool


class PlatformOverview(BaseModel):
    workspace_count: int
    active_workspace_count: int
    user_count: int
    active_user_count: int
    active_session_count: int
    integration_account_count: int
    failed_email_count: int
    subscription_status: Literal["not_configured"] = "not_configured"
    providers: list[ProviderStatus]


class PlatformWorkspaceList(BaseModel):
    workspaces: list[PlatformWorkspace]


class PlatformUserList(BaseModel):
    users: list[PlatformUser]


class WorkspaceStatusUpdate(BaseModel):
    status: Literal["active", "suspended"]


class UserStatusUpdate(BaseModel):
    is_active: bool
