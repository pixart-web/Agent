from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.integrations.email.schemas import EmailAccountOutput


class EmailConnectOutput(BaseModel):
    authorization_url: str


class EmailDisconnectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID


class EmailIntegrationStatus(BaseModel):
    enabled: bool
    provider: str
    send_enabled: bool
    mark_read_enabled: bool
    connected_accounts: int
    operational_state: str
    unresolved_writes: int
    pending_writes: int
    failed_writes: int
    last_sync_at: datetime | None


class EmailAccountsOutput(BaseModel):
    accounts: list[EmailAccountOutput]
