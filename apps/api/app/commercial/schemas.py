from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
    seat_limit: int
    monthly_token_limit: int
    automation_limit: int
    storage_limit_mb: int
    retention_days: int
    integrations: list[str]
    support_level: str


class SubscriptionRead(BaseModel):
    id: str
    workspace_id: str
    plan: PlanRead
    status: str
    billing_provider: str | None
    current_period_start: datetime
    current_period_end: datetime
    trial_ends_at: datetime | None
    cancel_at_period_end: bool
    cancelled_at: datetime | None
    ai_tokens_used: int
    automation_runs_used: int
    storage_bytes_used: int
    billing_configuration_status: str = "not_configured"
    invoice_links: list[str] = Field(default_factory=list)


class EntitlementDecision(BaseModel):
    allowed: bool
    entitlement: str
    used: int | None = None
    limit: int | None = None
    reason: str | None = None
