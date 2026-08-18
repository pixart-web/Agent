from app.agents.base import SpecializedAgent
from app.agents.exceptions import AgentNotRegisteredError
from app.agents.specialists.development import AGENT as DEVELOPMENT
from app.agents.specialists.marketing import AGENT as MARKETING
from app.agents.specialists.sales import AGENT as SALES
from app.agents.specialists.support import AGENT as SUPPORT


class SpecializedAgentRegistry:
    def __init__(self, agents: tuple[SpecializedAgent, ...] = ()) -> None:
        self._agents = {agent.agent_id: agent for agent in agents}

    def get(self, agent_id: str) -> SpecializedAgent:
        try:
            return self._agents[agent_id]
        except KeyError as error:
            raise AgentNotRegisteredError(
                f"Specialized agent '{agent_id}' is not registered"
            ) from error

    def list(self) -> list[SpecializedAgent]:
        return list(self._agents.values())


def build_agent_registry() -> SpecializedAgentRegistry:
    return SpecializedAgentRegistry((MARKETING, SALES, SUPPORT, DEVELOPMENT))
