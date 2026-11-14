from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictNotificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NotificationRead(StrictNotificationModel):
    id: UUID
    kind: str
    title: str
    body: str
    href: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(StrictNotificationModel):
    notifications: list[NotificationRead]
    unread_count: int


class NotificationPreferenceRead(StrictNotificationModel):
    in_app_enabled: bool
    email_enabled: bool
    enabled_kinds: list[str]


class NotificationPreferenceUpdate(StrictNotificationModel):
    in_app_enabled: bool
    email_enabled: bool
    enabled_kinds: list[str] = Field(default_factory=list, max_length=20)
