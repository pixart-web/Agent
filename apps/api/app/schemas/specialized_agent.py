from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.workflow_enums import AgentRunStatus, RiskLevel
from app.schemas.execution import TaskActionRead


class AgentActionProposal(BaseModel):
    tool_name: str = Field(min_length=1, max_length=128)
    tool_version: str = Field(default="1", min_length=1, max_length=32)
    input_payload: dict[str, object]
    reason: str = Field(min_length=1, max_length=2000)
    expected_outcome: str = Field(min_length=1, max_length=2000)
    risk_level: RiskLevel = RiskLevel.GREEN
    sequence: int = Field(ge=1)


class AgentProposal(BaseModel):
    summary: str = Field(min_length=1, max_length=5000)
    actions: list[AgentActionProposal] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sequences(self) -> "AgentProposal":
        sequences = [action.sequence for action in self.actions]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Action sequences must be unique")
        return self


class AgentRunRequest(BaseModel):
    feedback: str | None = None


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    agent_id: str
    user_id: UUID
    status: AgentRunStatus
    provider: str
    model: str
    prompt_version: str
    user_feedback: str | None
    proposal_summary: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    latency_ms: int | None
    error_code: str | None
    error_message: str | None
    correlation_id: UUID
    created_at: datetime
    completed_at: datetime | None


class AgentRunResponse(BaseModel):
    run: AgentRunRead
    actions: list[TaskActionRead]


class AgentCapabilitiesRead(BaseModel):
    id: str
    name: str
    description: str
    prompt_version: str
    allowed_tools: list[str]
    default_risk_policy: RiskLevel
    max_actions: int


class AgentOverviewRead(BaseModel):
    capabilities: AgentCapabilitiesRead
    tasks_pending: int
    tasks_running: int
    tasks_waiting_approval: int
    tasks_failed: int
    recent_runs: list[AgentRunRead]
    completed_runs: int
    failed_runs: int
    success_rate: float


class AgentReassignmentRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=32)
