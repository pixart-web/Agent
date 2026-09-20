from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.db.session import SessionLocal
from app.execution.context import ExecutionContext
from app.marketing.errors import (
    MarketingConflictError,
    MarketingNotFoundError,
    MarketingValidationError,
)
from app.marketing.schemas import (
    AssetCreateInput,
    AssetOutput,
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
    ContentHistoryOutput,
    ContentInput,
    ContentListInput,
    ContentOutput,
    ContentScheduleInput,
    ContentsOutput,
    ContentTransitionInput,
    ContentUpdateInput,
    MetricCreateInput,
    MetricOutput,
    MetricsListInput,
    MetricsOutput,
    PublicationOutput,
    PublicationRecordInput,
)
from app.models.client_management import CrmClient
from app.models.command import Command
from app.models.marketing import (
    MarketingAsset,
    MarketingCampaign,
    MarketingContent,
    MarketingContentHistory,
    MarketingPerformanceMetric,
    MarketingPublication,
)
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.workflow_enums import ActorType
from app.services.audit_service import AuditService

TRANSITIONS: dict[str, frozenset[str]] = {
    "idea": frozenset({"draft", "archived"}),
    "draft": frozenset({"review", "archived"}),
    "review": frozenset({"draft", "approved", "archived"}),
    "approved": frozenset({"draft", "scheduled", "archived"}),
    "scheduled": frozenset({"approved", "published", "archived"}),
    "published": frozenset({"archived"}),
    "archived": frozenset(),
}


class MarketingService:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self.session_factory = session_factory

    def list_campaigns(
        self, context: ExecutionContext, value: CampaignListInput
    ) -> CampaignsOutput:
        with self.session_factory() as session:
            query = (
                select(MarketingCampaign)
                .where(MarketingCampaign.user_id == context.user_id)
                .order_by(MarketingCampaign.updated_at.desc(), MarketingCampaign.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.status:
                query = query.where(MarketingCampaign.status == value.status)
            if value.client_id:
                self._client(session, context.user_id, value.client_id)
                query = query.where(MarketingCampaign.client_id == value.client_id)
            if value.query:
                query = query.where(MarketingCampaign.name.icontains(value.query, autoescape=True))
            campaigns = list(session.scalars(query))
            return CampaignsOutput(
                campaigns=[self._campaign_output(item) for item in campaigns],
                limit=value.limit,
                offset=value.offset,
            )

    def get_campaign(self, context: ExecutionContext, value: CampaignInput) -> CampaignOutput:
        with self.session_factory() as session:
            return self._campaign_output(
                self._campaign(session, context.user_id, value.campaign_id)
            )

    def list_content(self, context: ExecutionContext, value: ContentListInput) -> ContentsOutput:
        with self.session_factory() as session:
            self._campaign(session, context.user_id, value.campaign_id)
            query = (
                select(MarketingContent)
                .where(
                    MarketingContent.user_id == context.user_id,
                    MarketingContent.campaign_id == value.campaign_id,
                )
                .order_by(MarketingContent.updated_at.desc(), MarketingContent.id)
                .offset(value.offset)
                .limit(value.limit)
            )
            if value.status:
                query = query.where(MarketingContent.lifecycle_status == value.status)
            content = list(session.scalars(query))
            return ContentsOutput(
                content=[self._content_output(item) for item in content],
                limit=value.limit,
                offset=value.offset,
            )

    def get_content(self, context: ExecutionContext, value: ContentInput) -> ContentDetailOutput:
        with self.session_factory() as session:
            content = self._content(session, context.user_id, value.content_id)
            history = list(
                session.scalars(
                    select(MarketingContentHistory)
                    .where(
                        MarketingContentHistory.user_id == context.user_id,
                        MarketingContentHistory.content_id == content.id,
                    )
                    .order_by(
                        MarketingContentHistory.created_at,
                        MarketingContentHistory.id,
                    )
                )
            )
            assets = list(
                session.scalars(
                    select(MarketingAsset)
                    .where(
                        MarketingAsset.user_id == context.user_id,
                        MarketingAsset.content_id == content.id,
                    )
                    .order_by(MarketingAsset.created_at, MarketingAsset.id)
                )
            )
            publications = list(
                session.scalars(
                    select(MarketingPublication)
                    .where(
                        MarketingPublication.user_id == context.user_id,
                        MarketingPublication.content_id == content.id,
                    )
                    .order_by(
                        MarketingPublication.published_at,
                        MarketingPublication.id,
                    )
                )
            )
            metrics = list(
                session.scalars(
                    select(MarketingPerformanceMetric)
                    .where(
                        MarketingPerformanceMetric.user_id == context.user_id,
                        MarketingPerformanceMetric.content_id == content.id,
                    )
                    .order_by(
                        MarketingPerformanceMetric.measured_at.desc(),
                        MarketingPerformanceMetric.id,
                    )
                )
            )
            return ContentDetailOutput(
                content=self._content_output(content),
                history=[self._history_output(item) for item in history],
                assets=[self._asset_output(item) for item in assets],
                publications=[self._publication_output(item) for item in publications],
                metrics=[self._metric_output(item) for item in metrics],
            )

    def list_content_calendar(
        self, context: ExecutionContext, value: ContentCalendarInput
    ) -> ContentCalendarOutput:
        with self.session_factory() as session:
            query = (
                select(MarketingContent)
                .where(
                    MarketingContent.user_id == context.user_id,
                    MarketingContent.scheduled_for >= value.starts_at,
                    MarketingContent.scheduled_for < value.ends_at,
                )
                .order_by(MarketingContent.scheduled_for, MarketingContent.id)
            )
            if value.campaign_id:
                self._campaign(session, context.user_id, value.campaign_id)
                query = query.where(MarketingContent.campaign_id == value.campaign_id)
            content = list(session.scalars(query))
            return ContentCalendarOutput(
                content=[self._content_output(item) for item in content],
                starts_at=value.starts_at,
                ends_at=value.ends_at,
            )

    def list_metrics(self, context: ExecutionContext, value: MetricsListInput) -> MetricsOutput:
        with self.session_factory() as session:
            self._campaign(session, context.user_id, value.campaign_id)
            metrics = list(
                session.scalars(
                    select(MarketingPerformanceMetric)
                    .where(
                        MarketingPerformanceMetric.user_id == context.user_id,
                        MarketingPerformanceMetric.campaign_id == value.campaign_id,
                    )
                    .order_by(
                        MarketingPerformanceMetric.measured_at.desc(),
                        MarketingPerformanceMetric.id,
                    )
                    .offset(value.offset)
                    .limit(value.limit)
                )
            )
            return MetricsOutput(
                metrics=[self._metric_output(item) for item in metrics],
                limit=value.limit,
                offset=value.offset,
            )

    def create_campaign(
        self, context: ExecutionContext, value: CampaignCreateInput
    ) -> CampaignOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(MarketingCampaign).where(
                    MarketingCampaign.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._campaign_output(existing)
            if value.client_id:
                self._client(session, context.user_id, value.client_id)
            campaign = MarketingCampaign(
                user_id=context.user_id,
                client_id=value.client_id,
                owner_user_id=context.user_id,
                name=self._display(value.name),
                objective=value.objective,
                status=value.status,
                starts_at=value.starts_at,
                ends_at=value.ends_at,
                created_by_action_id=context.action_id,
            )
            session.add(campaign)
            session.flush()
            self._audit(
                session,
                context,
                "marketing_campaign_created",
                "marketing_campaign",
                campaign.id,
            )
            session.commit()
            return self._campaign_output(campaign)

    def update_campaign(
        self, context: ExecutionContext, value: CampaignUpdateInput
    ) -> CampaignOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            campaign = self._campaign(session, context.user_id, value.campaign_id, lock=True)
            if value.name is not None:
                campaign.name = self._display(value.name)
            if value.objective is not None:
                campaign.objective = value.objective
            if value.status is not None:
                campaign.status = value.status
            if value.clear_starts_at or value.starts_at is not None:
                campaign.starts_at = None if value.clear_starts_at else value.starts_at
            if value.clear_ends_at or value.ends_at is not None:
                campaign.ends_at = None if value.clear_ends_at else value.ends_at
            if campaign.starts_at and campaign.ends_at and campaign.ends_at <= campaign.starts_at:
                raise MarketingValidationError("Campaign end must be after its start")
            self._audit(
                session,
                context,
                "marketing_campaign_updated",
                "marketing_campaign",
                campaign.id,
            )
            session.commit()
            return self._campaign_output(campaign)

    def create_content(self, context: ExecutionContext, value: ContentCreateInput) -> ContentOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(MarketingContent).where(
                    MarketingContent.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._content_output(existing)
            self._campaign(session, context.user_id, value.campaign_id)
            if value.task_id:
                self._task(session, context.user_id, value.task_id)
            content = MarketingContent(
                user_id=context.user_id,
                campaign_id=value.campaign_id,
                task_id=value.task_id,
                content_type=value.content_type,
                channel=self._display(value.channel),
                title=self._display(value.title),
                body=value.body,
                lifecycle_status=value.lifecycle_status,
                created_by_action_id=context.action_id,
            )
            session.add(content)
            session.flush()
            self._history(
                session,
                context,
                content,
                None,
                content.lifecycle_status,
                "content_created",
            )
            self._audit(
                session,
                context,
                "marketing_content_created",
                "marketing_content",
                content.id,
            )
            session.commit()
            return self._content_output(content)

    def update_content(self, context: ExecutionContext, value: ContentUpdateInput) -> ContentOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            content = self._content(session, context.user_id, value.content_id, lock=True)
            if content.lifecycle_status not in {"idea", "draft"}:
                raise MarketingConflictError("Content must return to draft before editing")
            if value.title is not None:
                content.title = self._display(value.title)
            if value.body is not None:
                content.body = value.body
            if value.channel is not None:
                content.channel = self._display(value.channel)
            self._history(
                session,
                context,
                content,
                content.lifecycle_status,
                content.lifecycle_status,
                "content_fields_updated",
            )
            self._audit(
                session,
                context,
                "marketing_content_updated",
                "marketing_content",
                content.id,
            )
            session.commit()
            return self._content_output(content)

    def transition_content(
        self, context: ExecutionContext, value: ContentTransitionInput
    ) -> ContentOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            content = self._content(session, context.user_id, value.content_id, lock=True)
            previous = content.lifecycle_status
            self._require_transition(previous, value.target_status)
            content.lifecycle_status = value.target_status
            if value.target_status != "scheduled":
                content.scheduled_for = None
            self._history(
                session,
                context,
                content,
                previous,
                value.target_status,
                value.reason,
            )
            self._audit(
                session,
                context,
                "marketing_content_transitioned",
                "marketing_content",
                content.id,
            )
            session.commit()
            return self._content_output(content)

    def schedule_content(
        self, context: ExecutionContext, value: ContentScheduleInput
    ) -> ContentOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            content = self._content(session, context.user_id, value.content_id, lock=True)
            if value.scheduled_for <= utc_now():
                raise MarketingValidationError("Scheduled content must be in the future")
            previous = content.lifecycle_status
            self._require_transition(previous, "scheduled")
            content.lifecycle_status = "scheduled"
            content.scheduled_for = value.scheduled_for
            self._history(
                session,
                context,
                content,
                previous,
                "scheduled",
                value.reason,
            )
            self._audit(
                session,
                context,
                "marketing_content_scheduled",
                "marketing_content",
                content.id,
            )
            session.commit()
            return self._content_output(content)

    def record_publication(
        self, context: ExecutionContext, value: PublicationRecordInput
    ) -> PublicationOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(MarketingPublication).where(
                    MarketingPublication.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._publication_output(existing)
            content = self._content(session, context.user_id, value.content_id, lock=True)
            if content.lifecycle_status not in {"approved", "scheduled"}:
                raise MarketingConflictError(
                    "Only approved or scheduled content can be recorded as published"
                )
            if self._display(value.channel) != content.channel:
                raise MarketingValidationError(
                    "Publication channel does not match the content channel"
                )
            if value.published_at > utc_now():
                raise MarketingValidationError("Publication confirmation cannot be in the future")
            duplicate = session.scalar(
                select(MarketingPublication).where(
                    MarketingPublication.user_id == context.user_id,
                    MarketingPublication.content_id == content.id,
                    MarketingPublication.external_reference == value.external_reference,
                )
            )
            if duplicate:
                raise MarketingConflictError("Publication reference is already recorded")
            previous = content.lifecycle_status
            content.lifecycle_status = "published"
            content.scheduled_for = None
            publication = MarketingPublication(
                user_id=context.user_id,
                content_id=content.id,
                channel=self._display(value.channel),
                external_reference=value.external_reference,
                published_at=value.published_at,
                created_by_action_id=context.action_id,
            )
            session.add(publication)
            session.flush()
            self._history(
                session,
                context,
                content,
                previous,
                "published",
                "external_publication_confirmed",
            )
            self._audit(
                session,
                context,
                "marketing_publication_recorded",
                "marketing_publication",
                publication.id,
            )
            session.commit()
            return self._publication_output(publication)

    def add_asset_metadata(self, context: ExecutionContext, value: AssetCreateInput) -> AssetOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(MarketingAsset).where(
                    MarketingAsset.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._asset_output(existing)
            campaign_id = value.campaign_id
            if value.content_id:
                content = self._content(session, context.user_id, value.content_id)
                if campaign_id and campaign_id != content.campaign_id:
                    raise MarketingValidationError("Asset campaign does not match its content")
                campaign_id = content.campaign_id
            if campaign_id:
                self._campaign(session, context.user_id, campaign_id)
            asset = MarketingAsset(
                user_id=context.user_id,
                campaign_id=campaign_id,
                content_id=value.content_id,
                name=self._display(value.name),
                media_type=value.media_type,
                locator=value.locator,
                metadata_payload=value.metadata,
                created_by_action_id=context.action_id,
            )
            session.add(asset)
            session.flush()
            self._audit(
                session,
                context,
                "marketing_asset_metadata_added",
                "marketing_asset",
                asset.id,
            )
            session.commit()
            return self._asset_output(asset)

    def record_metric(self, context: ExecutionContext, value: MetricCreateInput) -> MetricOutput:
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            self._approved_action(session, context, payload)
            existing = session.scalar(
                select(MarketingPerformanceMetric).where(
                    MarketingPerformanceMetric.created_by_action_id == context.action_id
                )
            )
            if existing:
                return self._metric_output(existing)
            campaign_id = value.campaign_id
            if value.content_id:
                content = self._content(session, context.user_id, value.content_id)
                if campaign_id and campaign_id != content.campaign_id:
                    raise MarketingValidationError("Metric campaign does not match its content")
                campaign_id = content.campaign_id
            if campaign_id:
                self._campaign(session, context.user_id, campaign_id)
            metric = MarketingPerformanceMetric(
                user_id=context.user_id,
                campaign_id=campaign_id,
                content_id=value.content_id,
                metric_name=self._display(value.metric_name),
                value=Decimal(str(value.value)),
                source=self._display(value.source),
                measured_at=value.measured_at,
                metadata_payload=value.metadata,
                created_by_action_id=context.action_id,
            )
            session.add(metric)
            session.flush()
            self._audit(
                session,
                context,
                "marketing_metric_recorded",
                "marketing_performance_metric",
                metric.id,
            )
            session.commit()
            return self._metric_output(metric)

    @staticmethod
    def _approved_action(
        session: Session,
        context: ExecutionContext,
        payload: dict[str, object],
    ) -> None:
        action = session.scalar(
            select(TaskAction).where(TaskAction.id == context.action_id).with_for_update()
        )
        if action is None or action.input_payload != payload:
            raise MarketingValidationError(
                "Approved marketing payload does not match execution payload"
            )

    @staticmethod
    def _campaign(
        session: Session,
        user_id: UUID,
        campaign_id: UUID,
        *,
        lock: bool = False,
    ) -> MarketingCampaign:
        query = select(MarketingCampaign).where(
            MarketingCampaign.id == campaign_id,
            MarketingCampaign.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        campaign = session.scalar(query)
        if campaign is None:
            raise MarketingNotFoundError("Campaign was not found")
        return campaign

    @staticmethod
    def _content(
        session: Session,
        user_id: UUID,
        content_id: UUID,
        *,
        lock: bool = False,
    ) -> MarketingContent:
        query = select(MarketingContent).where(
            MarketingContent.id == content_id,
            MarketingContent.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        content = session.scalar(query)
        if content is None:
            raise MarketingNotFoundError("Content was not found")
        return content

    @staticmethod
    def _client(session: Session, user_id: UUID, client_id: UUID) -> CrmClient:
        client = session.scalar(
            select(CrmClient).where(
                CrmClient.id == client_id,
                CrmClient.user_id == user_id,
            )
        )
        if client is None:
            raise MarketingNotFoundError("Client was not found")
        return client

    @staticmethod
    def _task(session: Session, user_id: UUID, task_id: UUID) -> Task:
        task = session.scalar(
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Task.id == task_id, Command.user_id == user_id)
        )
        if task is None:
            raise MarketingNotFoundError("Task was not found")
        return task

    @staticmethod
    def _require_transition(previous: str, target: str) -> None:
        if target not in TRANSITIONS[previous]:
            raise MarketingConflictError(f"Content cannot transition from {previous} to {target}")

    @staticmethod
    def _history(
        session: Session,
        context: ExecutionContext,
        content: MarketingContent,
        previous: str | None,
        target: str,
        reason: str | None,
    ) -> None:
        session.add(
            MarketingContentHistory(
                user_id=context.user_id,
                content_id=content.id,
                from_status=previous,
                to_status=target,
                reason=reason,
                actor_action_id=context.action_id,
            )
        )

    @staticmethod
    def _campaign_output(value: MarketingCampaign) -> CampaignOutput:
        return CampaignOutput(
            id=value.id,
            client_id=value.client_id,
            owner_user_id=value.owner_user_id,
            name=value.name,
            objective=value.objective,
            status=value.status,
            starts_at=value.starts_at,
            ends_at=value.ends_at,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _content_output(value: MarketingContent) -> ContentOutput:
        return ContentOutput(
            id=value.id,
            campaign_id=value.campaign_id,
            task_id=value.task_id,
            content_type=value.content_type,
            channel=value.channel,
            title=value.title,
            body=value.body,
            lifecycle_status=value.lifecycle_status,
            scheduled_for=value.scheduled_for,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )

    @staticmethod
    def _history_output(
        value: MarketingContentHistory,
    ) -> ContentHistoryOutput:
        return ContentHistoryOutput(
            id=value.id,
            from_status=value.from_status,
            to_status=value.to_status,
            reason=value.reason,
            created_at=value.created_at,
        )

    @staticmethod
    def _asset_output(value: MarketingAsset) -> AssetOutput:
        return AssetOutput(
            id=value.id,
            campaign_id=value.campaign_id,
            content_id=value.content_id,
            name=value.name,
            media_type=value.media_type,
            locator=value.locator,
            metadata=value.metadata_payload,
            created_at=value.created_at,
        )

    @staticmethod
    def _publication_output(
        value: MarketingPublication,
    ) -> PublicationOutput:
        return PublicationOutput(
            id=value.id,
            content_id=value.content_id,
            channel=value.channel,
            external_reference=value.external_reference,
            published_at=value.published_at,
            created_at=value.created_at,
        )

    @staticmethod
    def _metric_output(
        value: MarketingPerformanceMetric,
    ) -> MetricOutput:
        return MetricOutput(
            id=value.id,
            campaign_id=value.campaign_id,
            content_id=value.content_id,
            metric_name=value.metric_name,
            value=float(value.value),
            source=value.source,
            measured_at=value.measured_at,
            metadata=value.metadata_payload,
            created_at=value.created_at,
        )

    @staticmethod
    def _display(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _audit(
        session: Session,
        context: ExecutionContext,
        event_type: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        AuditService(session).record(
            actor_type=ActorType.WORKER,
            actor_id=context.user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={},
            correlation_id=context.correlation_id,
        )
