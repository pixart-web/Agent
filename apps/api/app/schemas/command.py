from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workflow_enums import CommandStatus


class CommandCreate(BaseModel):
    input: str = Field(min_length=1, max_length=10_000)

    @field_validator("input")
    @classmethod
    def normalize_input(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Command input cannot be blank")
        return normalized


class CommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    input: str
    status: CommandStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
