from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.schemas.agent import AgentSeed


@dataclass(frozen=True)
class SeedResult:
    created: int
    updated: int


class AgentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Agent]:
        statement = select(Agent).order_by(Agent.created_at, Agent.id)
        return list(self.session.scalars(statement))

    def get(self, agent_id: str) -> Agent | None:
        return self.session.get(Agent, agent_id)

    def seed(self, agents: tuple[AgentSeed, ...]) -> SeedResult:
        created = 0
        updated = 0

        for agent_data in agents:
            agent = self.get(agent_data.id)
            values = agent_data.model_dump()

            if agent is None:
                self.session.add(Agent(**values))
                created += 1
                continue

            changed = False
            for field in ("name", "description", "status"):
                value = values[field]
                if getattr(agent, field) != value:
                    setattr(agent, field, value)
                    changed = True

            if changed:
                updated += 1

        self.session.commit()
        return SeedResult(created=created, updated=updated)
