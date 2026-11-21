from dataclasses import replace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.runner import AgentRunnerService, is_lookup_tool
from app.core.config import get_settings
from app.crm.schemas import CrmContactsOutput
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.workflow_enums import AgentRunStatus, RiskLevel
from app.schemas.specialized_agent import AgentActionProposal, AgentProposal
from tests.fakes import FakeLLMProvider
from tests.test_specialized_agents import outcome, proposal, ready_task

CONTACT_ID = uuid4()


class FakeContactSearch:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, context, payload) -> CrmContactsOutput:
        self.calls += 1
        return CrmContactsOutput(
            contacts=[
                {
                    "id": CONTACT_ID,
                    "organization_id": None,
                    "full_name": "Ana Lisboa",
                    "job_title": "Buyer",
                    "website": None,
                    "status": "active",
                    "source": "test",
                    "methods": [],
                    "addresses": [],
                    "tags": [],
                    "created_at": "2026-11-21T10:00:00Z",
                    "updated_at": "2026-11-21T10:00:00Z",
                }
            ],
            limit=payload.limit,
            offset=payload.offset,
        )


def tools_with_fake_search() -> tuple[ToolRegistry, FakeContactSearch]:
    fake = FakeContactSearch()
    registry = ToolRegistry()
    for definition in build_tool_registry().definitions():
        if definition.name == "crm.search_contacts":
            definition = replace(definition, handler=fake)
        registry.register(definition)
    return registry, fake


def search(query: str = "Ana") -> AgentProposal:
    return AgentProposal(
        summary="Find the contact first",
        actions=[
            AgentActionProposal(
                tool_name="crm.search_contacts",
                tool_version="1",
                input_payload={"query": query},
                reason="The task names no contact id",
                expected_outcome="The contact record",
                risk_level=RiskLevel.GREEN,
                sequence=1,
            )
        ],
    )


def owner(db: Session) -> User:
    return db.scalar(select(User).where(User.email == "agent@example.com"))


def offered_tools(call: dict) -> set[str]:
    schema = call["response_model"].model_json_schema()
    return {
        variant["properties"]["tool_name"]["const"]
        for variant in schema["$defs"].values()
        if "tool_name" in variant.get("properties", {})
    }


def test_only_internal_read_tools_are_lookups() -> None:
    tools = {item.name: item for item in build_tool_registry().definitions()}
    assert is_lookup_tool(tools["crm.search_contacts"])
    assert is_lookup_tool(tools["marketing.list_campaigns"])
    assert is_lookup_tool(tools["knowledge.search"])
    assert not is_lookup_tool(tools["crm.create_contact"])
    assert not is_lookup_tool(tools["email.search"])  # external account: never auto-run
    assert not is_lookup_tool(tools["internal.create_note"])


def test_agent_searches_then_acts_on_the_record_it_found(
    client: TestClient, db_session: Session
) -> None:
    _headers, _command, task = ready_task(client, db_session, "sales")
    registry, fake = tools_with_fake_search()
    provider = FakeLLMProvider([outcome(search()), outcome(proposal("internal.create_note"))])
    result = AgentRunnerService(db_session, provider, tool_registry=registry).run(
        UUID(task["id"]), owner(db_session).id
    )

    assert fake.calls == 1
    assert len(provider.calls) == 2
    first, second = provider.calls
    assert "crm.update_contact" not in offered_tools(first)  # no ids known yet
    assert "Read-only lookups already done" in second["user_prompt"]
    assert str(CONTACT_ID) in second["user_prompt"]
    assert "crm.update_contact" in offered_tools(second)  # the found id unlocks it
    assert result.run.status == AgentRunStatus.COMPLETED
    assert [action.tool_name for action in result.actions] == ["internal.create_note"]
    assert db_session.scalar(
        select(AuditLog).where(AuditLog.event_type == "agent_lookup_performed")
    )


def test_an_unusable_second_answer_keeps_the_lookup_proposal(
    client: TestClient, db_session: Session
) -> None:
    _headers, _command, task = ready_task(client, db_session, "sales")
    registry, _fake = tools_with_fake_search()
    provider = FakeLLMProvider(
        [outcome(search()), outcome(proposal("github.create_issue"))]  # outside the allowlist
    )
    result = AgentRunnerService(db_session, provider, tool_registry=registry).run(
        UUID(task["id"]), owner(db_session).id
    )
    assert result.run.status == AgentRunStatus.COMPLETED
    assert [action.tool_name for action in result.actions] == ["crm.search_contacts"]


def test_no_lookup_round_when_the_task_already_names_a_record(
    client: TestClient, db_session: Session
) -> None:
    _headers, _command, task = ready_task(client, db_session, "sales")
    from app.models.task import Task

    row = db_session.get(Task, UUID(task["id"]))
    row.instructions = f"Update contact {uuid4()} with the new phone number."
    db_session.commit()
    registry, fake = tools_with_fake_search()
    provider = FakeLLMProvider([outcome(search())])
    AgentRunnerService(db_session, provider, tool_registry=registry).run(
        UUID(task["id"]), owner(db_session).id
    )
    assert fake.calls == 0
    assert len(provider.calls) == 1


def test_lookup_round_can_be_switched_off_and_skips_mixed_proposals(
    client: TestClient, db_session: Session
) -> None:
    _headers, _command, task = ready_task(client, db_session, "sales")
    registry, fake = tools_with_fake_search()
    settings = get_settings().model_copy(update={"agent_lookup_round_enabled": False})
    provider = FakeLLMProvider([outcome(search())])
    AgentRunnerService(db_session, provider, tool_registry=registry, settings=settings).run(
        UUID(task["id"]), owner(db_session).id
    )
    assert fake.calls == 0 and len(provider.calls) == 1
