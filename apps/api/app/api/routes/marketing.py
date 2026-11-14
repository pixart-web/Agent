from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.execution.context import ExecutionContext
from app.integrations.credentials import EnvironmentCredentialProvider
from app.marketing.errors import (
    MarketingConflictError,
    MarketingNotFoundError,
    MarketingValidationError,
)
from app.marketing.schemas import (
    CampaignCreateInput,
    CampaignInput,
    CampaignListInput,
    CampaignOutput,
    CampaignsOutput,
    CampaignUpdateInput,
    ContentCalendarInput,
    ContentCalendarOutput,
    ContentCreateInput,
    ContentDetailOutput,
    ContentInput,
    ContentListInput,
    ContentOutput,
    ContentScheduleInput,
    ContentsOutput,
    ContentTransitionInput,
    ContentUpdateInput,
    MetricsListInput,
    MetricsOutput,
)
from app.marketing.service import MarketingService
from app.models.knowledge import WorkspaceMember
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


def _require_editor(db: Session, user: User) -> None:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace edit permission is required")


def _raise_marketing(error: Exception) -> None:
    if isinstance(error, MarketingNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, MarketingConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/campaigns", response_model=CampaignOutput, status_code=status.HTTP_201_CREATED)
def create_campaign(
    value: CampaignCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CampaignOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_campaign(_context(user.id), value, governed=False)
    except (MarketingNotFoundError, MarketingConflictError, MarketingValidationError) as error:
        _raise_marketing(error)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOutput)
def update_campaign(
    campaign_id: UUID,
    value: CampaignUpdateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CampaignOutput:
    _require_editor(db, user)
    if value.campaign_id != campaign_id:
        raise HTTPException(status_code=422, detail="Campaign id does not match path")
    try:
        return _service(db).update_campaign(_context(user.id), value, governed=False)
    except (MarketingNotFoundError, MarketingConflictError, MarketingValidationError) as error:
        _raise_marketing(error)


@router.post("/content", response_model=ContentOutput, status_code=status.HTTP_201_CREATED)
def create_content(
    value: ContentCreateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentOutput:
    _require_editor(db, user)
    try:
        return _service(db).create_content(_context(user.id), value, governed=False)
    except (MarketingNotFoundError, MarketingConflictError, MarketingValidationError) as error:
        _raise_marketing(error)


@router.patch("/content/{content_id}", response_model=ContentOutput)
def update_content(
    content_id: UUID,
    value: ContentUpdateInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentOutput:
    _require_editor(db, user)
    if value.content_id != content_id:
        raise HTTPException(status_code=422, detail="Content id does not match path")
    try:
        return _service(db).update_content(_context(user.id), value, governed=False)
    except (MarketingNotFoundError, MarketingConflictError, MarketingValidationError) as error:
        _raise_marketing(error)


@router.post("/content/{content_id}/transition", response_model=ContentOutput)
def transition_content(
    content_id: UUID,
    value: ContentTransitionInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentOutput:
    _require_editor(db, user)
    if value.content_id != content_id:
        raise HTTPException(status_code=422, detail="Content id does not match path")
    try:
        return _service(db).transition_content(_context(user.id), value, governed=False)
    except (MarketingNotFoundError, MarketingConflictError, MarketingValidationError) as error:
        _raise_marketing(error)


@router.post("/content/{content_id}/schedule", response_model=ContentOutput)
def schedule_content(
    content_id: UUID,
    value: ContentScheduleInput,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentOutput:
    _require_editor(db, user)
    if value.content_id != content_id:
        raise HTTPException(status_code=422, detail="Content id does not match path")
    try:
        return _service(db).schedule_content(_context(user.id), value, governed=False)
    except (MarketingNotFoundError, MarketingConflictError, MarketingValidationError) as error:
        _raise_marketing(error)


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
