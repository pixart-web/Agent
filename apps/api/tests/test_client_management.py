from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.crm.client_schemas import (
    ClientCreateInput,
    ClientInput,
    OpportunityCreateInput,
    PipelineCreateInput,
    ProjectCreateInput,
)
from app.crm.client_service import ClientManagementService
from app.crm.errors import CrmValidationError
from app.execution.context import ExecutionContext
from app.execution.tools.registry import build_tool_registry
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.client_management import (
    CrmClient,
    CrmOpportunity,
    CrmRecordHistory,
)
from app.models.crm import CrmActivity, CrmContact, CrmNote, CrmOrganization
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
        action_fingerprint="c" * 64,
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


def test_client_management_tool_catalog_enforces_risk_and_agent_boundaries() -> None:
    registry = build_tool_registry(settings=settings())
    client_360 = registry.get("crm.get_client_360", "1")
    create_opportunity = registry.get("crm.create_opportunity", "1")
    update_project = registry.get("crm.update_project", "1")

    assert client_360.risk_level == RiskLevel.GREEN
    assert client_360.requires_approval is False
    assert client_360.agent_types == frozenset({"sales", "support", "marketing"})
    assert create_opportunity.risk_level == RiskLevel.YELLOW
    assert create_opportunity.requires_approval is True
    assert create_opportunity.max_retries == 0
    assert create_opportunity.agent_types == frozenset({"sales"})
    assert update_project.agent_types == frozenset({"sales", "support"})


def test_client_360_aggregates_owned_business_context_and_labels_facts(client, db_session) -> None:
    email = "client-360@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "sales", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    organization = CrmOrganization(
        user_id=user.id,
        name="Sporting CP Demo",
        normalized_name="sporting cp demo",
        website="https://sporting-demo.example",
        status="active",
        source="synthetic-test",
    )
    db_session.add(organization)
    db_session.flush()
    contact = CrmContact(
        user_id=user.id,
        organization_id=organization.id,
        full_name="João Sponsor Demo",
        normalized_name="joao sponsor demo",
        job_title="Commercial Director",
        website="https://sponsor-demo.example",
        status="active",
        source="synthetic-test",
    )
    db_session.add(contact)
    db_session.flush()
    db_session.add_all(
        [
            CrmActivity(
                user_id=user.id,
                contact_id=contact.id,
                activity_type="email_linked",
                subject="Email reference linked",
                details={"provider": "gmail", "message_id": "synthetic-message"},
                source="integration_reference",
            ),
            CrmActivity(
                user_id=user.id,
                organization_id=organization.id,
                activity_type="calendar_linked",
                subject="Calendar event reference linked",
                details={
                    "provider": "google_calendar",
                    "event_id": "synthetic-event",
                },
                source="integration_reference",
            ),
            CrmNote(
                user_id=user.id,
                organization_id=organization.id,
                body="Untrusted synthetic relationship note.",
                source="synthetic-test",
            ),
        ]
    )
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = ClientManagementService(factory)
    task_id = UUID(task_data["id"])

    client_input = ClientCreateInput(
        organization_id=organization.id,
        lifecycle_status="active",
        industry="Sports",
        summary="Synthetic client used only for automated tests.",
    )
    crm_client = service.create_client(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_client",
            payload=client_input.model_dump(mode="json"),
        ),
        client_input,
    )

    pipeline_input = PipelineCreateInput(
        name="Commercial",
        is_default=True,
        stages=[
            {
                "name": "Discovery",
                "position": 1,
                "default_probability": 20,
            },
            {
                "name": "Won",
                "position": 2,
                "default_probability": 100,
                "is_terminal": True,
            },
        ],
    )
    pipeline = service.create_pipeline(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_pipeline",
            payload=pipeline_input.model_dump(mode="json"),
        ),
        pipeline_input,
    )
    project_input = ProjectCreateInput(
        client_id=crm_client.id,
        name="Sponsorship launch",
        status="active",
    )
    service.create_project(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_project",
            payload=project_input.model_dump(mode="json"),
        ),
        project_input,
    )
    opportunity_input = OpportunityCreateInput(
        client_id=crm_client.id,
        contact_id=contact.id,
        pipeline_id=pipeline.id,
        stage_id=pipeline.stages[0].id,
        title="Synthetic sponsorship",
        amount_minor=250_000,
        currency="eur",
    )
    service.create_opportunity(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_opportunity",
            payload=opportunity_input.model_dump(mode="json"),
        ),
        opportunity_input,
    )

    result = service.get_client_360(
        ExecutionContext(
            user_id=user.id,
            command_id=uuid4(),
            task_id=task_id,
            action_id=uuid4(),
            execution_id=uuid4(),
            correlation_id=uuid4(),
            credentials=EnvironmentCredentialProvider(),
        ),
        ClientInput(client_id=crm_client.id),
    )

    assert result.client.organization.name == "Sporting CP Demo"
    assert [item.full_name for item in result.contacts] == ["João Sponsor Demo"]
    assert len(result.emails) == 1
    assert len(result.meetings) == 1
    assert len(result.projects) == 1
    assert len(result.opportunities) == 1
    assert len(result.notes) == 1
    assert result.history
    assert all(item.kind == "fact" for item in result.insights)
    assert all(item.provenance == "system_fact" for item in result.insights)
    assert not any(item.kind == "model_summary" for item in result.insights)


def test_client_360_endpoint_hides_another_users_client(client, db_session) -> None:
    owner_headers, _command, _task = ready_task(
        client, db_session, "sales", email="client-owner@example.com"
    )
    register(client, "client-other@example.com")
    users = {item.email: item for item in db_session.query(User).all()}
    organization = CrmOrganization(
        user_id=users["client-other@example.com"].id,
        name="Other Client",
        normalized_name="other client",
        status="active",
        source="test",
    )
    db_session.add(organization)
    db_session.flush()
    crm_client = CrmClient(
        user_id=users["client-other@example.com"].id,
        organization_id=organization.id,
        owner_user_id=users["client-other@example.com"].id,
        lifecycle_status="active",
    )
    db_session.add(crm_client)
    db_session.commit()

    response = client.get(
        f"/api/v1/crm/clients/{crm_client.id}/360",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Client was not found"}


def test_opportunity_rejects_contact_from_another_client(client, db_session) -> None:
    email = "opportunity-owner@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "sales", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    organizations = [
        CrmOrganization(
            user_id=user.id,
            name=name,
            normalized_name=name.casefold(),
            status="active",
            source="test",
        )
        for name in ("Client A", "Client B")
    ]
    db_session.add_all(organizations)
    db_session.flush()
    foreign_contact = CrmContact(
        user_id=user.id,
        organization_id=organizations[1].id,
        full_name="Different Client Contact",
        normalized_name="different client contact",
        status="active",
        source="test",
    )
    db_session.add(foreign_contact)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = ClientManagementService(factory)
    task_id = UUID(task_data["id"])
    client_input = ClientCreateInput(organization_id=organizations[0].id)
    crm_client = service.create_client(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_client",
            payload=client_input.model_dump(mode="json"),
        ),
        client_input,
    )
    pipeline_input = PipelineCreateInput(
        name="Default",
        stages=[
            {
                "name": "Open",
                "position": 1,
                "default_probability": 10,
            }
        ],
    )
    pipeline = service.create_pipeline(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_pipeline",
            payload=pipeline_input.model_dump(mode="json"),
        ),
        pipeline_input,
    )
    opportunity_input = OpportunityCreateInput(
        client_id=crm_client.id,
        contact_id=foreign_contact.id,
        pipeline_id=pipeline.id,
        stage_id=pipeline.stages[0].id,
        title="Invalid cross-client opportunity",
    )
    operation_context = approved_context(
        db_session,
        user_id=user.id,
        task_id=task_id,
        tool_name="crm.create_opportunity",
        payload=opportunity_input.model_dump(mode="json"),
    )

    with pytest.raises(CrmValidationError, match="Contact does not belong"):
        service.create_opportunity(operation_context, opportunity_input)

    assert db_session.scalar(select(CrmOpportunity)) is None


def test_client_mutations_write_record_history(client, db_session) -> None:
    email = "history-owner@example.com"
    _headers, _command, task_data = ready_task(client, db_session, "sales", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    organization = CrmOrganization(
        user_id=user.id,
        name="History Client",
        normalized_name="history client",
        status="active",
        source="test",
    )
    db_session.add(organization)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = ClientManagementService(factory)
    task_id = UUID(task_data["id"])
    value = ClientCreateInput(organization_id=organization.id)

    service.create_client(
        approved_context(
            db_session,
            user_id=user.id,
            task_id=task_id,
            tool_name="crm.create_client",
            payload=value.model_dump(mode="json"),
        ),
        value,
    )

    history = db_session.scalar(select(CrmRecordHistory))
    assert history.entity_type == "client"
    assert history.event_type == "created"
    assert history.user_id == user.id
    assert history.changes["organization_id"] == str(organization.id)
