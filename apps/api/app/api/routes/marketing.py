from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.execution.context import ExecutionContext
from app.integrations.credentials import EnvironmentCredentialProvider
from app.marketing.schemas import (
    CampaignInput,
    CampaignListInput,
    CampaignOutput,
    CampaignsOutput,
    ContentCalendarInput,
    ContentCalendarOutput,
    ContentDetailOutput,
    ContentInput,
    ContentListInput,
    ContentsOutput,
    MetricsListInput,
    MetricsOutput,
)
from app.marketing.service import MarketingService
from app.models.user import User

router = APIRouter(prefix="/marketing", tags=["marketing"])


def _context(user_id: UUID) -> ExecutionContext:
    identifier = uuid4()
    return ExecutionContext(
        user_id=user_id,
        command_id=identifier,
        task_id=identifier,
        action_id=identifier,
        execution_id=identifier,
        correlation_id=identifier,
        credentials=EnvironmentCredentialProvider(),
    )


def _service(db: Session) -> MarketingService:
    return MarketingService(sessionmaker(bind=db.get_bind(), expire_on_commit=False))


@router.get("/campaigns", response_model=CampaignsOutput)
def list_campaigns(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    campaign_status: Literal["idea", "active", "paused", "completed", "archived"] | None = Query(
        default=None, alias="status"
    ),
    client_id: UUID | None = None,
    query: str | None = Query(default=None, min_length=1, max_length=255),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> CampaignsOutput:
    return _service(db).list_campaigns(
        _context(user.id),
        CampaignListInput(
            status=campaign_status,
            client_id=client_id,
            query=query,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignOutput)
def get_campaign(
    campaign_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CampaignOutput:
    return _service(db).get_campaign(_context(user.id), CampaignInput(campaign_id=campaign_id))


@router.get("/campaigns/{campaign_id}/content", response_model=ContentsOutput)
def list_content(
    campaign_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    content_status: Literal[
        "idea", "draft", "review", "approved", "scheduled", "published", "archived"
    ]
    | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> ContentsOutput:
    return _service(db).list_content(
        _context(user.id),
        ContentListInput(
            campaign_id=campaign_id,
            status=content_status,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/content/{content_id}", response_model=ContentDetailOutput)
def get_content(
    content_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentDetailOutput:
    return _service(db).get_content(_context(user.id), ContentInput(content_id=content_id))


@router.get("/calendar", response_model=ContentCalendarOutput)
def list_content_calendar(
    starts_at: datetime,
    ends_at: datetime,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    campaign_id: UUID | None = None,
) -> ContentCalendarOutput:
    return _service(db).list_content_calendar(
        _context(user.id),
        ContentCalendarInput(
            starts_at=starts_at,
            ends_at=ends_at,
            campaign_id=campaign_id,
        ),
    )


@router.get(
    "/campaigns/{campaign_id}/metrics",
    response_model=MetricsOutput,
)
def list_metrics(
    campaign_id: UUID,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=10_000),
) -> MetricsOutput:
    return _service(db).list_metrics(
        _context(user.id),
        MetricsListInput(
            campaign_id=campaign_id,
            limit=limit,
            offset=offset,
        ),
    )
