from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.workflow_enums import RiskLevel, TaskPriority, TaskStatus
from app.schemas.agent import AgentId


class TaskCreate(BaseModel):
    agent_id: AgentId
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=10_000)
    priority: TaskPriority = TaskPriority.NORMAL
    risk_level: RiskLevel = RiskLevel.GREEN
    sequence: int = Field(default=1, ge=1, le=10_000)

    @field_validator("title", "instructions")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: AgentId | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    instructions: str | None = Field(default=None, min_length=1, max_length=10_000)
    priority: TaskPriority | None = None
    risk_level: RiskLevel | None = None
    sequence: int | None = Field(default=None, ge=1, le=10_000)

    @field_validator("title", "instructions")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "TaskUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class TaskTransition(BaseModel):
    status: TaskStatus
    reason: str | None = Field(default=None, max_length=2_000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class TaskStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    from_status: TaskStatus | None
    to_status: TaskStatus
    changed_by_user_id: UUID | None
    reason: str | None
    created_at: datetime


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    agent_id: str
    title: str
    instructions: str
    status: TaskStatus
    priority: TaskPriority
    risk_level: RiskLevel
    sequence: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class TaskDetail(TaskRead):
    history: list[TaskStatusHistoryRead]
