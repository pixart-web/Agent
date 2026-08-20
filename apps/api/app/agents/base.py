from dataclasses import dataclass
from typing import Protocol

from app.agents.context import AgentTaskContext
from app.ai.base import LLMProvider, LLMResult
from app.models.workflow_enums import RiskLevel
from app.schemas.specialized_agent import AgentProposal


class SpecializedAgent(Protocol):
    agent_id: str
    name: str
    description: str
    prompt_version: str
    allowed_tools: frozenset[str]
    default_risk_policy: RiskLevel
    max_actions_per_task: int

    def propose_actions(
        self, *, context: AgentTaskContext, provider: LLMProvider
    ) -> LLMResult[AgentProposal]: ...


@dataclass(frozen=True)
class AgentDefinition:
    implementation: SpecializedAgent
