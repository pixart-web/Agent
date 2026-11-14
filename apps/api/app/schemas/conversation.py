from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.workflow_enums import PlanStatus, SupervisorRunStatus
from app.schemas.command import CommandRead


class ConversationCreate(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message cannot be blank")
        return normalized


class ConversationMessageCreate(ConversationCreate):
    pass


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    author_user_id: UUID | None
    command_id: UUID | None
    role: str
    content: str
    created_at: datetime


class ConversationTurnRead(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]
    command: CommandRead


class ConversationPlanRead(BaseModel):
    id: UUID
    title: str
    objective: str
    status: PlanStatus


class ConversationOperationRead(BaseModel):
    command: CommandRead
    plan: ConversationPlanRead | None
    supervisor_status: SupervisorRunStatus | None
    task_counts: dict[str, int]
    pending_approvals: int
    latest_error: str | None


class ConversationDetailRead(BaseModel):
    conversation: ConversationRead
    messages: list[ConversationMessageRead]
    operations: list[ConversationOperationRead]
