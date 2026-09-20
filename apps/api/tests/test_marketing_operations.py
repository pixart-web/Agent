from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.time import utc_now
from app.execution.context import ExecutionContext
from app.execution.tools.registry import build_tool_registry
from app.integrations.credentials import EnvironmentCredentialProvider
from app.marketing.errors import MarketingConflictError, MarketingValidationError
from app.marketing.schemas import (
    AssetCreateInput,
    CampaignCreateInput,
    ContentCalendarInput,
    ContentCreateInput,
    ContentInput,
    ContentScheduleInput,
    ContentTransitionInput,
    ContentUpdateInput,
    PublicationRecordInput,
)
from app.marketing.service import MarketingService
from app.models.marketing import (
    MarketingContent,
    MarketingContentHistory,
    MarketingPublication,
)
from app.models.task_action import TaskAction
from app.models.user import User
from app.models.workflow_enums import ActorType, RiskLevel, TaskActionStatus
from tests.test_execution_engine import register
from tests.test_specialized_agents import ready_task


def settings() -> Settings:
    return Settings(auth_secret_key="test-only-auth-secret-with-at-least-32-characters")


def approved_context(
    db_session,
    *,
    user_id: UUID,
    task_id: UUID,
    tool_name: str,
    payload: dict[str, object],
) -> ExecutionContext:
    action = TaskAction(
        task_id=task_id,
        tool_name=tool_name,
        tool_version="1",
        input_payload=payload,
        risk_level=RiskLevel.YELLOW,
        status=TaskActionStatus.RUNNING,
        created_by_type=ActorType.USER,
        action_fingerprint="d" * 64,
        correlation_id=uuid4(),
    )
    db_session.add(action)
    db_session.commit()
    return ExecutionContext(
        user_id=user_id,
        command_id=uuid4(),
        task_id=task_id,
        action_id=action.id,
        execution_id=uuid4(),
        correlation_id=action.correlation_id,
        credentials=EnvironmentCredentialProvider(),
    )


def execute(
    db_session,
    service: MarketingService,
    *,
    user_id: UUID,
    task_id: UUID,
    operation: str,
    value,
):
    return getattr(service, operation)(
        approved_context(
            db_session,
            user_id=user_id,
            task_id=task_id,
            tool_name=f"marketing.{operation}",
            payload=value.model_dump(mode="json"),
        ),
        value,
    )


def test_marketing_catalog_has_governed_reads_and_no_publish_tool() -> None:
    registry = build_tool_registry(settings=settings())
    read = registry.get("marketing.list_content_calendar", "1")
    schedule = registry.get("marketing.schedule_content", "1")
    record = registry.get("marketing.record_publication", "1")

    assert read.risk_level == RiskLevel.GREEN
    assert read.requires_approval is False
    assert schedule.risk_level == RiskLevel.YELLOW
    assert schedule.requires_approval is True
    assert schedule.max_retries == 0
    assert record.description.find("No tool in this catalog publishes externally") >= 0
    assert "marketing.publish" not in {definition.name for definition in registry.definitions()}


def test_synthetic_campaign_lifecycle_schedules_then_records_confirmation(
    client, db_session
) -> None:
    email = "marketing-owner@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "marketing", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = MarketingService(factory)
    task_id = UUID(task_data["id"])

    campaign = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_campaign",
        value=CampaignCreateInput(
            name="Sporting Demo European Match",
            objective="Prepare synthetic, approval-gated match content.",
            status="active",
        ),
    )
    content = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_content",
        value=ContentCreateInput(
            campaign_id=campaign.id,
            task_id=task_id,
            content_type="social_post",
            channel="social-demo",
            title="European match draft",
            body="Synthetic draft only. Nothing is published.",
            lifecycle_status="draft",
        ),
    )
    for target in ("review", "approved"):
        content = execute(
            db_session,
            service,
            user_id=user.id,
            task_id=task_id,
            operation="transition_content",
            value=ContentTransitionInput(
                content_id=content.id,
                target_status=target,
                reason=f"Move synthetic draft to {target}",
            ),
        )
    scheduled_for = utc_now() + timedelta(days=2)
    content = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="schedule_content",
        value=ContentScheduleInput(
            content_id=content.id,
            scheduled_for=scheduled_for,
            reason="Proposed demo slot",
        ),
    )

    assert content.lifecycle_status == "scheduled"
    assert db_session.scalar(select(MarketingPublication)) is None
    calendar = service.list_content_calendar(
        ExecutionContext(
            user_id=user.id,
            command_id=uuid4(),
            task_id=task_id,
            action_id=uuid4(),
            execution_id=uuid4(),
            correlation_id=uuid4(),
            credentials=EnvironmentCredentialProvider(),
        ),
        ContentCalendarInput(
            starts_at=utc_now(),
            ends_at=utc_now() + timedelta(days=7),
        ),
    )
    assert [item.id for item in calendar.content] == [content.id]

    publication = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="record_publication",
        value=PublicationRecordInput(
            content_id=content.id,
            external_reference="demo://confirmed-publication/1",
            published_at=utc_now(),
            channel="social-demo",
        ),
    )

    assert publication.external_reference.startswith("demo://")
    stored = db_session.get(MarketingContent, content.id)
    assert stored.lifecycle_status == "published"
    history = list(
        db_session.scalars(
            select(MarketingContentHistory).where(MarketingContentHistory.content_id == content.id)
        )
    )
    assert [item.to_status for item in history] == [
        "draft",
        "review",
        "approved",
        "scheduled",
        "published",
    ]


def test_content_cannot_skip_review_or_edit_after_approval(client, db_session) -> None:
    email = "marketing-lifecycle@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "marketing", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    service = MarketingService(sessionmaker(bind=db_session.get_bind(), expire_on_commit=False))
    task_id = UUID(task_data["id"])
    campaign = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_campaign",
        value=CampaignCreateInput(name="Lifecycle Demo", objective="Test lifecycle."),
    )
    content = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_content",
        value=ContentCreateInput(
            campaign_id=campaign.id,
            content_type="social_post",
            channel="demo",
            title="Draft",
            body="Draft body",
        ),
    )
    invalid = ContentTransitionInput(
        content_id=content.id,
        target_status="approved",
    )
    invalid_context = approved_context(
        db_session,
        user_id=user.id,
        task_id=task_id,
        tool_name="marketing.transition_content",
        payload=invalid.model_dump(mode="json"),
    )

    with pytest.raises(MarketingConflictError, match="cannot transition"):
        service.transition_content(invalid_context, invalid)

    for target in ("review", "approved"):
        execute(
            db_session,
            service,
            user_id=user.id,
            task_id=task_id,
            operation="transition_content",
            value=ContentTransitionInput(content_id=content.id, target_status=target),
        )
    edit = ContentUpdateInput(content_id=content.id, body="Changed after approval")
    edit_context = approved_context(
        db_session,
        user_id=user.id,
        task_id=task_id,
        tool_name="marketing.update_content",
        payload=edit.model_dump(mode="json"),
    )
    with pytest.raises(MarketingConflictError, match="return to draft"):
        service.update_content(edit_context, edit)


def test_marketing_endpoint_hides_another_users_campaign(client, db_session) -> None:
    owner_headers, _command, _task = ready_task(
        client, db_session, "marketing", email="marketing-api-owner@example.com"
    )
    register(client, "marketing-api-other@example.com")
    users = {item.email: item for item in db_session.query(User).all()}
    from app.models.marketing import MarketingCampaign

    campaign = MarketingCampaign(
        user_id=users["marketing-api-other@example.com"].id,
        owner_user_id=users["marketing-api-other@example.com"].id,
        name="Other Campaign",
        objective="Must remain private.",
        status="idea",
    )
    db_session.add(campaign)
    db_session.commit()

    response = client.get(
        f"/api/v1/marketing/campaigns/{campaign.id}",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Campaign was not found"}


def test_asset_metadata_rejects_mismatched_campaign_and_content(client, db_session) -> None:
    email = "marketing-asset@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "marketing", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    service = MarketingService(sessionmaker(bind=db_session.get_bind(), expire_on_commit=False))
    task_id = UUID(task_data["id"])
    campaigns = [
        execute(
            db_session,
            service,
            user_id=user.id,
            task_id=task_id,
            operation="create_campaign",
            value=CampaignCreateInput(
                name=f"Asset Campaign {index}",
                objective="Synthetic asset metadata test.",
            ),
        )
        for index in (1, 2)
    ]
    content = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_content",
        value=ContentCreateInput(
            campaign_id=campaigns[0].id,
            content_type="image",
            channel="demo",
            title="Asset content",
            body="Metadata only.",
        ),
    )
    value = AssetCreateInput(
        campaign_id=campaigns[1].id,
        content_id=content.id,
        name="Synthetic image",
        media_type="image/png",
        locator="asset://synthetic/1",
    )
    operation_context = approved_context(
        db_session,
        user_id=user.id,
        task_id=task_id,
        tool_name="marketing.add_asset_metadata",
        payload=value.model_dump(mode="json"),
    )

    with pytest.raises(MarketingValidationError, match="does not match"):
        service.add_asset_metadata(operation_context, value)


def test_content_detail_is_user_scoped(client, db_session) -> None:
    email = "marketing-detail-owner@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "marketing", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    service = MarketingService(sessionmaker(bind=db_session.get_bind(), expire_on_commit=False))
    task_id = UUID(task_data["id"])
    campaign = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_campaign",
        value=CampaignCreateInput(name="Detail Demo", objective="Detail test."),
    )
    content = execute(
        db_session,
        service,
        user_id=user.id,
        task_id=task_id,
        operation="create_content",
        value=ContentCreateInput(
            campaign_id=campaign.id,
            content_type="brief",
            channel="internal",
            title="Owned brief",
            body="Owned and untrusted content.",
        ),
    )

    detail = service.get_content(
        ExecutionContext(
            user_id=user.id,
            command_id=uuid4(),
            task_id=task_id,
            action_id=uuid4(),
            execution_id=uuid4(),
            correlation_id=uuid4(),
            credentials=EnvironmentCredentialProvider(),
        ),
        ContentInput(content_id=content.id),
    )

    assert detail.content.body == "Owned and untrusted content."
    assert detail.history[0].to_status == "draft"
