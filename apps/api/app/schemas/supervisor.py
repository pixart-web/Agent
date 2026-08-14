from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.workflow_enums import (
    RiskLevel,
    SupervisorRunStatus,
    TaskPriority,
)
from app.schemas.agent import AgentId
from app.schemas.plan import PlanRead
from app.schemas.task import TaskRead


class SupervisorTaskProposal(BaseModel):
    agent_id: AgentId
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, max_length=5_000)
    priority: TaskPriority
    risk_level: RiskLevel
    sequence: int = Field(ge=1, le=10_000)

    @field_validator("title", "instructions")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class SupervisorPlanProposal(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    objective: str = Field(min_length=1, max_length=10_000)
    reasoning_summary: str | None = Field(default=None, max_length=1_000)
    tasks: list[SupervisorTaskProposal] = Field(min_length=1)

    @field_validator("title", "objective", "reasoning_summary")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def require_unique_sequences(self) -> "SupervisorPlanProposal":
        sequences = [task.sequence for task in self.tasks]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Task sequences must be unique")
        return self


class SupervisorRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    command_id: UUID
    user_id: UUID
    status: SupervisorRunStatus
    provider: str
    model: str
    prompt_version: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: Decimal | None
    currency: str | None
    latency_ms: int | None
    request_id: str | None
    error_code: str | None
    error_message: str | None
    user_feedback: str | None
    created_at: datetime
    completed_at: datetime | None


class SupervisorPlanResponse(BaseModel):
    plan: PlanRead
    tasks: list[TaskRead]
    run: SupervisorRunRead


class PlanFeedback(BaseModel):
    reason: str = Field(min_length=1, max_length=5_000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class RegeneratePlanRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=5_000)

    @field_validator("feedback")
    @classmethod
    def normalize_feedback(cls, value: str) -> str:
        return value.strip()
