from typing import Literal

from pydantic import BaseModel

AgentId = Literal["supervisor", "marketing", "sales", "support", "development"]


class Agent(BaseModel):
    id: AgentId
    name: str
    description: str
    status: Literal["ready"] = "ready"
