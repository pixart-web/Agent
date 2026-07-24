from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

AgentId = Annotated[
    str,
    Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9-]*$"),
]


class AgentBase(BaseModel):
    name: str
    description: str
    status: str = "ready"


class AgentSeed(AgentBase):
    id: AgentId


class AgentRead(AgentSeed):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime
