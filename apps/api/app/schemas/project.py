from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.workflow_enums import CommandStatus, TaskStatus

ProjectStatus = Literal["planned", "active", "blocked", "completed", "cancelled"]
MilestoneStatus = Literal["pending", "completed"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    status: ProjectStatus = "planned"
    client_id: UUID | None = None
    starts_on: date | None = None
    due_on: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be blank")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreate":
        if self.starts_on and self.due_on and self.due_on < self.starts_on:
            raise ValueError("due_on cannot be before starts_on")
        return self


class ProjectUpdate(ProjectCreate):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: ProjectStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    client_id: UUID | None
    name: str
    description: str | None
    status: ProjectStatus
    starts_on: date | None
    due_on: date | None
    task_count: int = 0
    completed_task_count: int = 0
    progress_percentage: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectMemberCreate(BaseModel):
    user_id: UUID
    role: str = Field(default="member", min_length=1, max_length=64)

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.strip()


class ProjectMemberRead(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    email: str
    role: str
    created_at: datetime


class ProjectMilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    due_on: date | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip()


class ProjectMilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    due_on: date | None = None
    status: MilestoneStatus | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "ProjectMilestoneUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ProjectMilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    due_on: date | None
    status: MilestoneStatus
    created_at: datetime


class ProjectResourceLink(BaseModel):
    resource_id: UUID


class ProjectTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: TaskStatus
    agent_id: str


class ProjectCommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    input: str
    status: CommandStatus


class ProjectActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    event_type: str
    description: str
    created_at: datetime


class ProjectDetail(ProjectRead):
    members: list[ProjectMemberRead]
    milestones: list[ProjectMilestoneRead]
    tasks: list[ProjectTaskRead]
    commands: list[ProjectCommandRead]
    activity: list[ProjectActivityRead]
