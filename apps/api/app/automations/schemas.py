from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TriggerType = Literal[
    "schedule",
    "email_received",
    "calendar_event",
    "crm_change",
    "task_state",
    "manual",
    "webhook",
]
RunStatus = Literal["running", "completed", "skipped", "failed"]
ConditionOperator = Literal["eq", "not_eq", "in", "exists"]
_SENSITIVE_FIELD_MARKERS = (
    "password",
    "secret",
    "token",
    "api_key",
    "credential",
    "authorization",
    "cookie",
)


class StrictAutomationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AutomationCondition(StrictAutomationModel):
    field: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.]{0,127}$")
    operator: ConditionOperator
    value: object | None = None

    @field_validator("field")
    @classmethod
    def reject_sensitive_field(cls, value: str) -> str:
        normalized = value.lower().replace("-", "_")
        if any(marker in normalized for marker in _SENSITIVE_FIELD_MARKERS):
            raise ValueError("Sensitive fields cannot be used in automation conditions")
        return value

    @model_validator(mode="after")
    def validate_value(self) -> "AutomationCondition":
        if self.operator == "exists" and self.value is not None:
            raise ValueError("exists conditions do not accept a value")
        if self.operator == "in" and not isinstance(self.value, list):
            raise ValueError("in conditions require a list value")
        return self


_CONFIG_KEYS: dict[str, frozenset[str]] = {
    "schedule": frozenset({"interval_minutes"}),
    "email_received": frozenset({"account_id"}),
    "calendar_event": frozenset({"account_id", "calendar_id"}),
    "crm_change": frozenset({"entity_types", "change_types"}),
    "task_state": frozenset({"statuses"}),
    "manual": frozenset(),
    "webhook": frozenset({"source"}),
}


class AutomationCreate(StrictAutomationModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5_000)
    trigger_type: TriggerType
    trigger_config: dict[str, object] = Field(default_factory=dict)
    conditions: list[AutomationCondition] = Field(default_factory=list, max_length=20)
    command_template: str = Field(min_length=1, max_length=20_000)
    max_depth: int = Field(default=3, ge=0, le=10)
    max_runs_per_window: int = Field(default=20, ge=1, le=1_000)
    window_seconds: int = Field(default=3_600, ge=60, le=86_400)
    cooldown_seconds: int = Field(default=0, ge=0, le=86_400)
    next_run_at: datetime | None = None

    @field_validator("next_run_at")
    @classmethod
    def require_aware_schedule(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("next_run_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_trigger_config(self) -> "AutomationCreate":
        allowed = _CONFIG_KEYS[self.trigger_type]
        unknown = set(self.trigger_config) - allowed
        if unknown:
            raise ValueError("Trigger config contains unsupported fields")
        for key, item in self.trigger_config.items():
            if key in {"account_id", "calendar_id", "source"}:
                if not isinstance(item, str) or not item.strip() or len(item) > 255:
                    raise ValueError(f"{key} must be a non-empty bounded string")
                if key == "account_id":
                    try:
                        UUID(item)
                    except ValueError as error:
                        raise ValueError("account_id must be a UUID") from error
            if key in {"entity_types", "change_types", "statuses"} and (
                not isinstance(item, list)
                or not 1 <= len(item) <= 20
                or any(
                    not isinstance(entry, str) or not entry.strip() or len(entry) > 64
                    for entry in item
                )
            ):
                raise ValueError(f"{key} must be a bounded list of strings")
        if self.trigger_type == "schedule":
            interval = self.trigger_config.get("interval_minutes")
            if (
                not isinstance(interval, int)
                or isinstance(interval, bool)
                or not 5 <= interval <= 10_080
            ):
                raise ValueError("Schedule interval_minutes must be between 5 and 10080")
            if self.next_run_at is None:
                raise ValueError("Scheduled automations require next_run_at")
        elif self.next_run_at is not None:
            raise ValueError("next_run_at is only valid for scheduled automations")
        return self


class AutomationRead(StrictAutomationModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    enabled: bool
    trigger_type: TriggerType
    trigger_config: dict[str, object]
    conditions: list[AutomationCondition]
    command_template: str
    max_depth: int
    max_runs_per_window: int
    window_seconds: int
    cooldown_seconds: int
    next_run_at: datetime | None
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutomationList(StrictAutomationModel):
    automations: list[AutomationRead]
    limit: int
    offset: int


class AutomationTrigger(StrictAutomationModel):
    event_key: str = Field(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9._:/-]+$")
    payload: dict[str, object] = Field(default_factory=dict)
    parent_run_id: UUID | None = None


class AutomationRunRead(StrictAutomationModel):
    id: UUID
    automation_id: UUID
    trigger_type: TriggerType
    trigger_key: str
    status: RunStatus
    correlation_id: UUID
    causation_run_id: UUID | None
    depth: int
    command_id: UUID | None
    skipped_reason: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
    deduplicated: bool = False


class AutomationRunList(StrictAutomationModel):
    runs: list[AutomationRunRead]
    limit: int
    offset: int
