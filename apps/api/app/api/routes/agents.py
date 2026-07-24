from fastapi import APIRouter

from app.schemas.agent import Agent
from app.services.agent_service import list_agents

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[Agent])
async def agents() -> list[Agent]:
    return list_agents()
