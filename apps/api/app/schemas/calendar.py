from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CalendarAccountOutput(BaseModel):
    id: UUID
    provider: str
    account_type: str
    email_address: str
    status: str
    scopes: list[str]
    last_sync_at: datetime | None


class CalendarConnectOutput(BaseModel):
    authorization_url: str


class CalendarDisconnectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID


class CalendarIntegrationStatus(BaseModel):
    enabled: bool
    provider: str
    write_enabled: bool
    connected_accounts: int


class CalendarAccountsOutput(BaseModel):
    accounts: list[CalendarAccountOutput]
