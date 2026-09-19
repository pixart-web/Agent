from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.crm.schemas import (
    CrmActivityOutput,
    CrmContactOutput,
    CrmNoteOutput,
    CrmOrganizationOutput,
)


class StrictClientModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClientListInput(StrictClientModel):
    status: Literal["prospect", "active", "paused", "former", "archived"] | None = None
    query: str | None = Field(default=None, min_length=1, max_length=255)
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class ClientInput(StrictClientModel):
    client_id: UUID


class ClientCreateInput(StrictClientModel):
    organization_id: UUID
    lifecycle_status: Literal["prospect", "active", "paused", "former", "archived"] = "prospect"
    industry: str | None = Field(default=None, max_length=128)
    summary: str | None = Field(default=None, max_length=10_000)


class ClientUpdateInput(StrictClientModel):
    client_id: UUID
    lifecycle_status: Literal["prospect", "active", "paused", "former", "archived"] | None = None
    industry: str | None = Field(default=None, max_length=128)
    clear_industry: bool = False
    summary: str | None = Field(default=None, max_length=10_000)
    clear_summary: bool = False

    @model_validator(mode="after")
    def validate_update(self) -> "ClientUpdateInput":
        if self.clear_industry and self.industry is not None:
            raise ValueError("Cannot set and clear industry together")
        if self.clear_summary and self.summary is not None:
            raise ValueError("Cannot set and clear summary together")
        if (
            self.lifecycle_status is None
            and self.industry is None
            and not self.clear_industry
            and self.summary is None
            and not self.clear_summary
        ):
            raise ValueError("At least one client field must be updated")
        return self


class ClientOutput(StrictClientModel):
    id: UUID
    organization: CrmOrganizationOutput
    owner_user_id: UUID
    lifecycle_status: str
    industry: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime


class ClientsOutput(StrictClientModel):
    clients: list[ClientOutput]
    limit: int
    offset: int


class ProjectListInput(StrictClientModel):
    client_id: UUID
    status: Literal["planned", "active", "blocked", "completed", "cancelled"] | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class ProjectCreateInput(StrictClientModel):
    client_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    status: Literal["planned", "active", "blocked", "completed", "cancelled"] = "planned"
    starts_on: date | None = None
    due_on: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreateInput":
        if self.starts_on and self.due_on and self.due_on < self.starts_on:
            raise ValueError("Project due date cannot precede its start date")
        return self


class ProjectUpdateInput(StrictClientModel):
    project_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    clear_description: bool = False
    status: Literal["planned", "active", "blocked", "completed", "cancelled"] | None = None
    starts_on: date | None = None
    clear_starts_on: bool = False
    due_on: date | None = None
    clear_due_on: bool = False

    @model_validator(mode="after")
    def validate_update(self) -> "ProjectUpdateInput":
        if self.clear_description and self.description is not None:
            raise ValueError("Cannot set and clear description together")
        if self.clear_starts_on and self.starts_on is not None:
            raise ValueError("Cannot set and clear start date together")
        if self.clear_due_on and self.due_on is not None:
            raise ValueError("Cannot set and clear due date together")
        if (
            self.name is None
            and self.description is None
            and not self.clear_description
            and self.status is None
            and self.starts_on is None
            and not self.clear_starts_on
            and self.due_on is None
            and not self.clear_due_on
        ):
            raise ValueError("At least one project field must be updated")
        return self


class ProjectOutput(StrictClientModel):
    id: UUID
    client_id: UUID
    owner_user_id: UUID
    name: str
    description: str | None
    status: str
    starts_on: date | None
    due_on: date | None
    created_at: datetime
    updated_at: datetime


class ProjectsOutput(StrictClientModel):
    projects: list[ProjectOutput]
    limit: int
    offset: int


class PipelineStageInput(StrictClientModel):
    name: str = Field(min_length=1, max_length=128)
    position: int = Field(ge=1, le=100)
    default_probability: int = Field(default=0, ge=0, le=100)
    is_terminal: bool = False


class PipelineCreateInput(StrictClientModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2_000)
    is_default: bool = False
    stages: list[PipelineStageInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_stages(self) -> "PipelineCreateInput":
        positions = [stage.position for stage in self.stages]
        names = [stage.name.casefold() for stage in self.stages]
        if len(positions) != len(set(positions)):
            raise ValueError("Pipeline stage positions must be unique")
        if len(names) != len(set(names)):
            raise ValueError("Pipeline stage names must be unique")
        return self


class PipelineListInput(StrictClientModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class PipelineStageOutput(StrictClientModel):
    id: UUID
    name: str
    position: int
    default_probability: int
    is_terminal: bool


class PipelineOutput(StrictClientModel):
    id: UUID
    name: str
    description: str | None
    is_default: bool
    stages: list[PipelineStageOutput]
    created_at: datetime
    updated_at: datetime


class PipelinesOutput(StrictClientModel):
    pipelines: list[PipelineOutput]
    limit: int
    offset: int


class OpportunityListInput(StrictClientModel):
    client_id: UUID
    status: Literal["open", "won", "lost", "cancelled"] | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class OpportunityCreateInput(StrictClientModel):
    client_id: UUID
    contact_id: UUID | None = None
    pipeline_id: UUID
    stage_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    amount_minor: int = Field(default=0, ge=0, le=9_000_000_000_000)
    currency: str = Field(default="EUR", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    probability: int | None = Field(default=None, ge=0, le=100)
    status: Literal["open", "won", "lost", "cancelled"] = "open"
    expected_close_on: date | None = None


class OpportunityUpdateInput(StrictClientModel):
    opportunity_id: UUID
    stage_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)
    clear_description: bool = False
    amount_minor: int | None = Field(default=None, ge=0, le=9_000_000_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    probability: int | None = Field(default=None, ge=0, le=100)
    status: Literal["open", "won", "lost", "cancelled"] | None = None
    expected_close_on: date | None = None
    clear_expected_close_on: bool = False

    @model_validator(mode="after")
    def validate_update(self) -> "OpportunityUpdateInput":
        if self.clear_description and self.description is not None:
            raise ValueError("Cannot set and clear description together")
        if self.clear_expected_close_on and self.expected_close_on is not None:
            raise ValueError("Cannot set and clear expected close date together")
        changed = any(
            (
                self.stage_id,
                self.title,
                self.description,
                self.clear_description,
                self.amount_minor is not None,
                self.currency,
                self.probability is not None,
                self.status,
                self.expected_close_on,
                self.clear_expected_close_on,
            )
        )
        if not changed:
            raise ValueError("At least one opportunity field must be updated")
        return self


class OpportunityOutput(StrictClientModel):
    id: UUID
    client_id: UUID
    contact_id: UUID | None
    pipeline_id: UUID
    stage_id: UUID
    owner_user_id: UUID
    title: str
    description: str | None
    amount_minor: int
    currency: str
    probability: int
    status: str
    expected_close_on: date | None
    created_at: datetime
    updated_at: datetime


class OpportunitiesOutput(StrictClientModel):
    opportunities: list[OpportunityOutput]
    limit: int
    offset: int


class TaskLinkInput(StrictClientModel):
    client_id: UUID
    task_id: UUID
    project_id: UUID | None = None


class TaskSummary(StrictClientModel):
    id: UUID
    project_id: UUID | None
    title: str
    status: str
    agent_id: str
    created_at: datetime


class HistoryOutput(StrictClientModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    event_type: str
    changes: dict[str, object]
    created_at: datetime


class InsightOutput(StrictClientModel):
    kind: Literal["fact", "model_summary"]
    provenance: Literal["system_fact", "llm"]
    text: str
    generated_at: datetime | None = None


class Client360Output(StrictClientModel):
    client: ClientOutput
    contacts: list[CrmContactOutput]
    emails: list[CrmActivityOutput]
    meetings: list[CrmActivityOutput]
    projects: list[ProjectOutput]
    tasks: list[TaskSummary]
    activities: list[CrmActivityOutput]
    opportunities: list[OpportunityOutput]
    notes: list[CrmNoteOutput]
    history: list[HistoryOutput]
    insights: list[InsightOutput]
