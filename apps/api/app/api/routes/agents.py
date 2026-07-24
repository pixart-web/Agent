from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import AgentRead
from app.services.agent_service import AgentNotFoundError, AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
def list_agents(db: Annotated[Session, Depends(get_db)]) -> list[AgentRead]:
    return [AgentRead.model_validate(agent) for agent in AgentService(db).list_agents()]


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, db: Annotated[Session, Depends(get_db)]) -> AgentRead:
    try:
        agent = AgentService(db).get_agent(agent_id)
    except AgentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return AgentRead.model_validate(agent)
