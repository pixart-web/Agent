from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workflow_enums import PlanStatus


class PlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=10_000)

    @field_validator("title", "objective")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    command_id: UUID
    title: str
    objective: str
    reasoning_summary: str | None
    status: PlanStatus
    version: int
    is_current: bool
    rejection_reason: str | None
    approved_at: datetime | None
    approved_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
