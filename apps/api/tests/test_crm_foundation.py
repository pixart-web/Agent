from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.crm.schemas import (
    CrmContactMethodInput,
    CrmContactUpdateInput,
    CrmSearchContactsInput,
)
from app.crm.service import CrmService
from app.execution.context import ExecutionContext
from app.execution.policies import RetryPolicy
from app.execution.tools.registry import build_tool_registry
from app.execution.worker import ExecutionWorker
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.audit_log import AuditLog
from app.models.crm import (
    CrmActivity,
    CrmContact,
    CrmContactMethod,
    CrmOrganization,
)
from app.models.email_reference import EmailReference
from app.models.integration_account import IntegrationAccount
from app.models.task_action import TaskAction
from app.models.user import User
from app.models.workflow_enums import (
    ActorType,
    IntegrationAccountStatus,
    IntegrationAccountType,
    RiskLevel,
    TaskActionStatus,
)
from app.schemas.execution import ApprovalDecision, TaskActionCreate
from app.services.approval_service import ApprovalService
from app.services.execution_service import ExecutionService
from tests.test_execution_engine import register
from tests.test_specialized_agents import ready_task


def crm_settings() -> Settings:
    return Settings(auth_secret_key="test-only-auth-secret-with-at-least-32-characters")


def context(user_id: UUID) -> ExecutionContext:
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


def test_crm_method_validation_normalizes_email_and_rejects_short_phone() -> None:
    email = CrmContactMethodInput(
        method_type="email", value="Demo@Sponsor-Demo.Example", is_primary=True
    )
    assert email.value == "Demo@Sponsor-Demo.Example"
    with pytest.raises(ValueError):
        CrmContactMethodInput(method_type="phone", value="123")


def test_crm_tool_catalog_uses_green_reads_and_yellow_mutations() -> None:
    registry = build_tool_registry(settings=crm_settings())
    read = registry.get("crm.search_contacts", "1")
    create = registry.get("crm.create_contact", "1")

    assert read.risk_level == RiskLevel.GREEN
    assert read.requires_approval is False
    assert create.risk_level == RiskLevel.YELLOW
    assert create.requires_approval is True
    assert create.max_retries == 0
    assert "development" not in create.agent_types


def test_crm_contact_create_is_approved_audited_and_idempotent(client, db_session) -> None:
    email = "crm-owner@example.com"
    _headers, _command, task = ready_task(client, db_session, "sales", email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    service = CrmService(factory)
    registry = build_tool_registry(settings=crm_settings(), crm_service=service)
    workflow = ExecutionService(db_session, registry)
    payload = {
        "full_name": "João Sponsor Demo",
        "job_title": "Commercial Director",
        "website": "https://sponsor-demo.example/contact",
        "source": "sporting-demo",
        "methods": [
            {
                "method_type": "email",
                "value": "JOAO@sponsor-demo.example",
                "label": "work",
                "is_primary": True,
            }
        ],
        "address": {
            "kind": "business",
            "line1": "1 Demo Avenue",
            "city": "Lisbon",
            "country_code": "pt",
        },
        "tags": ["Sponsor", "Demo"],
    }
    action = workflow.create_action(
        UUID(task["id"]),
        user.id,
        TaskActionCreate(tool_name="crm.create_contact", tool_version="1", input_payload=payload),
    )
    approval = workflow.dispatch(action.id, user.id).approval

    assert "João Sponsor Demo" in approval.description
    assert "JOAO@sponsor-demo.example" in approval.description
    _approved, execution = ApprovalService(db_session).approve(
        approval.id, user.id, ApprovalDecision()
    )
    worker = ExecutionWorker(
        factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
    )
    result = worker.execute(execution.id)

    assert result.status.value == "succeeded"
    contact = db_session.scalar(select(CrmContact))
    assert contact.full_name == "João Sponsor Demo"
    assert contact.website == "https://sponsor-demo.example/contact"
    assert contact.created_by_action_id == action.id
    method = db_session.scalar(select(CrmContactMethod))
    assert method.normalized_value == "joao@sponsor-demo.example"
    assert db_session.scalar(select(AuditLog).where(AuditLog.event_type == "crm_contact_created"))
    assert worker.execute(execution.id) is None
    assert len(db_session.query(CrmContact).all()) == 1


def test_crm_does_not_merge_similar_names_or_shared_methods(db_session) -> None:
    user = User(
        email="crm-identity@example.com", password_hash="not-used", full_name="CRM Identity"
    )
    db_session.add(user)
    db_session.flush()
    contacts = [
        CrmContact(
            user_id=user.id,
            full_name=name,
            normalized_name="joao sponsor demo",
            status="active",
            source="test",
        )
        for name in ("João Sponsor Demo", "JOAO Sponsor Demo")
    ]
    db_session.add_all(contacts)
    db_session.flush()
    for contact in contacts:
        db_session.add(
            CrmContactMethod(
                user_id=user.id,
                contact_id=contact.id,
                method_type="email",
                value="shared@sponsor-demo.example",
                normalized_value="shared@sponsor-demo.example",
                is_primary=True,
            )
        )
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)

    result = CrmService(factory).search_contacts(
        context(user.id), CrmSearchContactsInput(query="shared@sponsor-demo.example")
    )

    assert len(result.contacts) == 2
    assert result.contacts[0].id != result.contacts[1].id


def test_crm_contact_endpoint_prevents_cross_user_access(client, db_session) -> None:
    first = register(client, "crm-api-owner@example.com")
    register(client, "crm-api-other@example.com")
    users = {item.email: item for item in db_session.query(User).all()}
    contact = CrmContact(
        user_id=users["crm-api-other@example.com"].id,
        full_name="Other User Contact",
        normalized_name="other user contact",
        status="active",
        source="test",
    )
    db_session.add(contact)
    db_session.commit()

    response = client.get(f"/api/v1/crm/contacts/{contact.id}", headers=first)

    assert response.status_code == 404
    assert response.json() == {"detail": "Contact was not found"}


def test_crm_link_email_rejects_reference_owned_by_another_user(client, db_session) -> None:
    email = "crm-link-owner@example.com"
    _headers, _command, task = ready_task(client, db_session, "sales", email=email)
    owner = db_session.scalar(select(User).where(User.email == email))
    other = User(email="crm-link-other@example.com", password_hash="not-used", full_name="Other")
    db_session.add(other)
    db_session.flush()
    contact = CrmContact(
        user_id=owner.id,
        full_name="Owned Contact",
        normalized_name="owned contact",
        status="active",
        source="test",
    )
    account = IntegrationAccount(
        user_id=other.id,
        provider="gmail",
        account_type=IntegrationAccountType.PERSONAL,
        external_account_id="other@example.com",
        email_address="other@example.com",
        status=IntegrationAccountStatus.CONNECTED,
        scopes=["gmail.readonly"],
        encrypted_credentials="test-only-ciphertext",
    )
    db_session.add_all([contact, account])
    db_session.flush()
    reference = EmailReference(provider="gmail", account_id=account.id, message_id="message-other")
    db_session.add(reference)
    db_session.commit()

    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    registry = build_tool_registry(settings=crm_settings(), crm_service=CrmService(factory))
    workflow = ExecutionService(db_session, registry)
    action = workflow.create_action(
        UUID(task["id"]),
        owner.id,
        TaskActionCreate(
            tool_name="crm.link_email",
            tool_version="1",
            input_payload={
                "contact_id": str(contact.id),
                "email_reference_id": str(reference.id),
            },
        ),
    )
    approval = workflow.dispatch(action.id, owner.id).approval
    _approved, execution = ApprovalService(db_session).approve(
        approval.id, owner.id, ApprovalDecision()
    )

    result = ExecutionWorker(
        factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
    ).execute(execution.id)

    assert result.status.value == "failed"
    assert db_session.scalar(select(CrmActivity)) is None


def test_crm_partial_update_preserves_omitted_organization_and_job_title(
    db_session,
) -> None:
    user = User(email="crm-partial@example.com", password_hash="not-used", full_name="Partial")
    organization = CrmOrganization(
        user_id=user.id,
        name="Sporting CP Demo",
        normalized_name="sporting cp demo",
        status="active",
        source="test",
    )
    db_session.add(user)
    db_session.flush()
    organization.user_id = user.id
    db_session.add(organization)
    db_session.flush()
    contact = CrmContact(
        user_id=user.id,
        organization_id=organization.id,
        full_name="João Sponsor Demo",
        normalized_name="joao sponsor demo",
        job_title="Commercial Director",
        website="https://sponsor-demo.example/original",
        status="active",
        source="test",
    )
    db_session.add(contact)
    db_session.flush()
    value = CrmContactUpdateInput(contact_id=contact.id, status="inactive")
    action = TaskAction(
        task_id=uuid4(),
        tool_name="crm.update_contact",
        tool_version="1",
        input_payload=value.model_dump(mode="json"),
        risk_level=RiskLevel.YELLOW,
        status=TaskActionStatus.RUNNING,
        created_by_type=ActorType.USER,
        action_fingerprint="b" * 64,
        correlation_id=uuid4(),
    )
    db_session.add(action)
    db_session.commit()
    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    execution_context = context(user.id)
    execution_context = ExecutionContext(
        user_id=user.id,
        command_id=execution_context.command_id,
        task_id=execution_context.task_id,
        action_id=action.id,
        execution_id=execution_context.execution_id,
        correlation_id=execution_context.correlation_id,
        credentials=execution_context.credentials,
    )

    output = CrmService(factory).update_contact(execution_context, value)

    assert output.status == "inactive"
    assert output.organization_id == organization.id
    assert output.job_title == "Commercial Director"
    assert output.website == "https://sponsor-demo.example/original"
