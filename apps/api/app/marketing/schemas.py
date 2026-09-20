from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictMarketingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


CampaignStatus = Literal["idea", "active", "paused", "completed", "archived"]
ContentStatus = Literal["idea", "draft", "review", "approved", "scheduled", "published", "archived"]


class CampaignListInput(StrictMarketingModel):
    status: CampaignStatus | None = None
    client_id: UUID | None = None
    query: str | None = Field(default=None, min_length=1, max_length=255)
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class CampaignInput(StrictMarketingModel):
    campaign_id: UUID


class CampaignCreateInput(StrictMarketingModel):
    client_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    objective: str = Field(min_length=1, max_length=20_000)
    status: CampaignStatus = "idea"
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "CampaignCreateInput":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Campaign end must be after its start")
        return self


class CampaignUpdateInput(StrictMarketingModel):
    campaign_id: UUID
    name: str | None = Field(default=None, min_length=1, max_length=255)
    objective: str | None = Field(default=None, min_length=1, max_length=20_000)
    status: CampaignStatus | None = None
    starts_at: datetime | None = None
    clear_starts_at: bool = False
    ends_at: datetime | None = None
    clear_ends_at: bool = False

    @model_validator(mode="after")
    def validate_update(self) -> "CampaignUpdateInput":
        if self.clear_starts_at and self.starts_at is not None:
            raise ValueError("Cannot set and clear campaign start together")
        if self.clear_ends_at and self.ends_at is not None:
            raise ValueError("Cannot set and clear campaign end together")
        if not any(
            (
                self.name,
                self.objective,
                self.status,
                self.starts_at,
                self.clear_starts_at,
                self.ends_at,
                self.clear_ends_at,
            )
        ):
            raise ValueError("At least one campaign field must be updated")
        return self


class CampaignOutput(StrictMarketingModel):
    id: UUID
    client_id: UUID | None
    owner_user_id: UUID
    name: str
    objective: str
    status: str
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CampaignsOutput(StrictMarketingModel):
    campaigns: list[CampaignOutput]
    limit: int
    offset: int


class ContentListInput(StrictMarketingModel):
    campaign_id: UUID
    status: ContentStatus | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10_000)


class ContentInput(StrictMarketingModel):
    content_id: UUID


class ContentCreateInput(StrictMarketingModel):
    campaign_id: UUID
    task_id: UUID | None = None
    content_type: Literal["brief", "social_post", "email", "article", "video", "image", "other"]
    channel: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=100_000)
    lifecycle_status: Literal["idea", "draft"] = "draft"


class ContentUpdateInput(StrictMarketingModel):
    content_id: UUID
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=100_000)
    channel: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_update(self) -> "ContentUpdateInput":
        if self.title is None and self.body is None and self.channel is None:
            raise ValueError("At least one content field must be updated")
        return self


class ContentTransitionInput(StrictMarketingModel):
    content_id: UUID
    target_status: Literal["draft", "review", "approved", "archived"]
    reason: str | None = Field(default=None, max_length=5_000)


class ContentScheduleInput(StrictMarketingModel):
    content_id: UUID
    scheduled_for: datetime
    reason: str | None = Field(default=None, max_length=5_000)


class PublicationRecordInput(StrictMarketingModel):
    content_id: UUID
    external_reference: str = Field(min_length=1, max_length=2048)
    published_at: datetime
    channel: str = Field(min_length=1, max_length=64)


class ContentOutput(StrictMarketingModel):
    id: UUID
    campaign_id: UUID
    task_id: UUID | None
    content_type: str
    channel: str
    title: str
    body: str
    lifecycle_status: str
    scheduled_for: datetime | None
    created_at: datetime
    updated_at: datetime


class ContentsOutput(StrictMarketingModel):
    content: list[ContentOutput]
    limit: int
    offset: int


class ContentHistoryOutput(StrictMarketingModel):
    id: UUID
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class ContentDetailOutput(StrictMarketingModel):
    content: ContentOutput
    history: list[ContentHistoryOutput]
    assets: list["AssetOutput"]
    publications: list["PublicationOutput"]
    metrics: list["MetricOutput"]


class ContentCalendarInput(StrictMarketingModel):
    starts_at: datetime
    ends_at: datetime
    campaign_id: UUID | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "ContentCalendarInput":
        if self.ends_at <= self.starts_at:
            raise ValueError("Calendar end must be after its start")
        if (self.ends_at - self.starts_at).days > 366:
            raise ValueError("Content calendar range cannot exceed 366 days")
        return self


class ContentCalendarOutput(StrictMarketingModel):
    content: list[ContentOutput]
    starts_at: datetime
    ends_at: datetime


class AssetCreateInput(StrictMarketingModel):
    campaign_id: UUID | None = None
    content_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    media_type: str = Field(min_length=1, max_length=128)
    locator: str = Field(min_length=1, max_length=2048)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> "AssetCreateInput":
        if self.campaign_id is None and self.content_id is None:
            raise ValueError("An asset must target a campaign or content item")
        return self


class AssetOutput(StrictMarketingModel):
    id: UUID
    campaign_id: UUID | None
    content_id: UUID | None
    name: str
    media_type: str
    locator: str
    metadata: dict[str, object]
    created_at: datetime


class PublicationOutput(StrictMarketingModel):
    id: UUID
    content_id: UUID
    channel: str
    external_reference: str
    published_at: datetime
    created_at: datetime


class MetricCreateInput(StrictMarketingModel):
    campaign_id: UUID | None = None
    content_id: UUID | None = None
    metric_name: str = Field(min_length=1, max_length=128)
    value: float = Field(ge=0, le=1_000_000_000_000)
    source: str = Field(min_length=1, max_length=128)
    measured_at: datetime
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> "MetricCreateInput":
        if self.campaign_id is None and self.content_id is None:
            raise ValueError("A metric must target a campaign or content item")
        return self


class MetricOutput(StrictMarketingModel):
    id: UUID
    campaign_id: UUID | None
    content_id: UUID | None
    metric_name: str
    value: float
    source: str
    measured_at: datetime
    metadata: dict[str, object]
    created_at: datetime


class MetricsListInput(StrictMarketingModel):
    campaign_id: UUID
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0, le=10_000)


class MetricsOutput(StrictMarketingModel):
    metrics: list[MetricOutput]
    limit: int
    offset: int
