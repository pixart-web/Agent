from dataclasses import dataclass

from app.agents.context import AgentTaskContext
from app.ai.base import LLMProvider, LLMResult
from app.models.workflow_enums import RiskLevel
from app.schemas.specialized_agent import AgentProposal


@dataclass(frozen=True)
class PromptSpecializedAgent:
    agent_id: str
    name: str
    description: str
    prompt_version: str
    system_prompt: str
    allowed_tools: frozenset[str]
    default_risk_policy: RiskLevel = RiskLevel.GREEN
    max_actions_per_task: int = 10

    def propose_actions(
        self, *, context: AgentTaskContext, provider: LLMProvider
    ) -> LLMResult[AgentProposal]:
        return provider.generate_structured(
            system_prompt=self.system_prompt,
            user_prompt=context.user_prompt(),
            response_model=AgentProposal,
        )
