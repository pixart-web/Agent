from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository, SeedResult
from app.schemas.agent import AgentSeed

INITIAL_AGENTS = (
    AgentSeed(
        id="supervisor",
        name="Supervisor",
        description="Coordinates priorities, delegates work, and tracks execution.",
    ),
    AgentSeed(
        id="marketing",
        name="Marketing",
        description="Supports campaigns, content operations, and brand workflows.",
    ),
    AgentSeed(
        id="sales",
        name="Sales",
        description="Assists pipeline management, proposals, and commercial follow-up.",
    ),
    AgentSeed(
        id="support",
        name="Support",
        description="Helps resolve customer requests and organize service knowledge.",
    ),
    AgentSeed(
        id="development",
        name="Development",
        description="Supports engineering delivery, quality, and technical operations.",
    ),
)


class AgentNotFoundError(Exception):
    def __init__(self, agent_id: str) -> None:
        super().__init__(f"Agent '{agent_id}' was not found")
        self.agent_id = agent_id


class AgentService:
    def __init__(self, session: Session) -> None:
        self.repository = AgentRepository(session)

    def list_agents(self) -> list[Agent]:
        return self.repository.list()

    def get_agent(self, agent_id: str) -> Agent:
        agent = self.repository.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(agent_id)
        return agent


def seed_initial_agents(session: Session) -> SeedResult:
    return AgentRepository(session).seed(INITIAL_AGENTS)
