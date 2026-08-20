from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workflow_enums import (
    ActorType,
    ApprovalStatus,
    RiskLevel,
    TaskActionStatus,
    TaskExecutionStatus,
)


class TaskActionCreate(BaseModel):
    tool_name: str = Field(min_length=1, max_length=128)
    tool_version: str = Field(default="1", min_length=1, max_length=32)
    input_payload: dict[str, object]
    risk_level: RiskLevel | None = None
    created_by_type: ActorType = ActorType.USER


class TaskActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    tool_name: str
    tool_version: str
    input_payload: dict[str, object]
    risk_level: RiskLevel
    status: TaskActionStatus
    created_by_type: ActorType
    created_by_id: UUID | None
    action_fingerprint: str
    correlation_id: UUID
    created_at: datetime
    updated_at: datetime


class TaskExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    task_action_id: UUID
    attempt_number: int
    status: TaskExecutionStatus
    tool_name: str
    tool_version: str
    input_payload: dict[str, object]
    output_payload: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    worker_id: str | None
    duration_ms: int | None
    correlation_id: UUID
    created_at: datetime
    updated_at: datetime


class DispatchResponse(BaseModel):
    action: TaskActionRead
    execution: TaskExecutionRead | None = None
    approval: "ApprovalRequestRead | None" = None


class ApprovalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    task_id: UUID
    task_action_id: UUID
    risk_level: RiskLevel
    title: str
    description: str
    status: ApprovalStatus
    action_fingerprint: str
    requested_at: datetime
    decided_at: datetime | None
    decided_by_user_id: UUID | None
    decision_reason: str | None
    expires_at: datetime | None
    correlation_id: UUID


class ApprovalDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2_000)
    confirm_high_risk: bool = False

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: UUID


class TaskDependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    depends_on_task_id: UUID


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_type: ActorType
    actor_id: UUID | None
    event_type: str
    resource_type: str
    resource_id: UUID
    metadata_payload: dict[str, object]
    created_at: datetime
    correlation_id: UUID


class PlanProgressRead(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    waiting_approval_tasks: int
    progress_percentage: float


DispatchResponse.model_rebuild()
