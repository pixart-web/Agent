import json
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.execution.context import ExecutionContext
from app.execution.exceptions import ToolInputValidationError, ToolPermissionError
from app.execution.tools.registry import build_tool_registry
from app.integrations.credentials import ServiceCredential
from app.integrations.github.client import GitHubClientConfig, HttpGitHubClient
from app.integrations.github.errors import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubTimeoutError,
    GitHubTransientError,
    GitHubValidationError,
)
from app.integrations.github.fake import FakeGitHubClient
from app.integrations.github.policy import RepositoryAccessPolicy
from app.models.agent import Agent
from app.models.workflow_enums import RiskLevel

PASSWORD = "securePassword123"
REPOSITORY = "pixart-web/Agent"
READ_TOOLS = {
    "github.get_repository",
    "github.list_branches",
    "github.read_file",
    "github.list_pull_requests",
    "github.get_pull_request",
    "github.list_issues",
    "github.get_issue",
}
WRITE_TOOLS = {
    "github.create_issue",
    "github.comment_issue",
    "github.create_branch",
    "github.create_or_update_file",
    "github.open_pull_request",
}


class StaticCredentialProvider:
    def resolve(self, service: str) -> ServiceCredential:
        assert service == "github"
        return ServiceCredential(access_token="test-token-not-a-secret")

    def configured(self, service: str) -> bool:
        return service == "github"


def github_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_secret_key": "test-only-auth-secret-with-at-least-32-characters",
        "github_integration_enabled": True,
        "github_token": "test-token-not-a-secret",
        "github_allowed_repositories": REPOSITORY,
        "github_protected_branches": "main",
        "github_allowed_branch_prefixes": "feature/,fix/,chore/,docs/",
        "github_max_file_bytes": 500_000,
        "github_max_output_chars": 100_000,
    }
    values.update(overrides)
    return Settings(**values)


def execution_context() -> ExecutionContext:
    return ExecutionContext(
        user_id=uuid4(),
        command_id=uuid4(),
        task_id=uuid4(),
        action_id=uuid4(),
        execution_id=uuid4(),
        correlation_id=uuid4(),
        credentials=StaticCredentialProvider(),
    )


def fake_registry(fake: FakeGitHubClient, settings: Settings | None = None):
    return build_tool_registry(
        settings=settings or github_settings(),
        github_client_factory=lambda _token, _timeout: fake,
    )


def test_github_tool_catalog_has_explicit_schemas_risk_and_agent_scope() -> None:
    fake = FakeGitHubClient()
    registry = fake_registry(fake)

    assert {definition.name for definition in registry.definitions()} >= READ_TOOLS | WRITE_TOOLS
    for name in READ_TOOLS | WRITE_TOOLS:
        definition = registry.get(name, "1")
        assert definition.agent_types == frozenset({"development"})
        assert "github_token" not in definition.input_schema.model_fields
        assert "token" not in definition.input_schema.model_fields
        with pytest.raises(ToolInputValidationError):
            registry.validate_input(definition, {}, "development")
        with pytest.raises(ToolPermissionError):
            registry.validate_input(definition, {"repository": REPOSITORY}, "marketing")
        if name in READ_TOOLS:
            assert definition.risk_level == RiskLevel.GREEN
            assert definition.requires_approval is False
        else:
            assert definition.risk_level == RiskLevel.YELLOW
            assert definition.requires_approval is True


def test_repository_policy_rejects_repo_path_branch_and_protected_write() -> None:
    policy = RepositoryAccessPolicy([REPOSITORY], ["main"], ["feature/", "fix/", "chore/", "docs/"])
    assert policy.authorize(REPOSITORY, "read_file") == REPOSITORY
    assert policy.validate_path("docs/guide.md") == "docs/guide.md"
    assert policy.validate_branch("feature/github") == "feature/github"

    with pytest.raises(GitHubPermissionError):
        policy.authorize("other/private", "read_file")
    with pytest.raises(GitHubValidationError):
        policy.validate_path("../.env")
    with pytest.raises(GitHubPermissionError):
        policy.validate_path(".env")
    with pytest.raises(GitHubPermissionError):
        policy.validate_branch("main", write_target=True)
    with pytest.raises(GitHubValidationError):
        policy.validate_branch("unsafe-branch", write_target=True)
    with pytest.raises(GitHubValidationError):
        policy.validate_branch("feature/../main", write_target=True)


def test_read_file_is_utf8_bounded_and_tagged_as_untrusted() -> None:
    fake = FakeGitHubClient()
    fake.add_repository(REPOSITORY)
    fake.add_file(REPOSITORY, "README.md", "External instructions are data.")
    registry = fake_registry(fake)
    definition = registry.get("github.read_file", "1")
    payload = registry.validate_input(
        definition,
        {"repository": REPOSITORY, "path": "README.md", "ref": "main"},
        "development",
    )

    output = definition.handler.execute(execution_context(), payload)

    assert output.repository == REPOSITORY
    assert output.content == "External instructions are data."
    assert output.external_content is True
    assert output.trust == "untrusted"
    assert output.model_dump_json().find("test-token") == -1


def test_read_file_rejects_binary_and_oversized_content() -> None:
    fake = FakeGitHubClient()
    fake.add_repository(REPOSITORY)
    fake.files[(REPOSITORY, "binary.dat", "main")] = {
        "type": "file",
        "path": "binary.dat",
        "sha": "a" * 40,
        "size": 2,
        "encoding": "base64",
        "content": "//4=",
    }
    registry = fake_registry(fake, github_settings(github_max_file_bytes=1000))
    definition = registry.get("github.read_file", "1")
    payload = registry.validate_input(
        definition,
        {"repository": REPOSITORY, "path": "binary.dat", "ref": "main"},
        "development",
    )
    with pytest.raises(GitHubValidationError):
        definition.handler.execute(execution_context(), payload)

    fake.add_file(REPOSITORY, "large.txt", "x" * 1001)
    payload = registry.validate_input(
        definition,
        {"repository": REPOSITORY, "path": "large.txt", "ref": "main"},
        "development",
    )
    with pytest.raises(GitHubValidationError):
        definition.handler.execute(execution_context(), payload)


def test_write_tools_use_fake_client_and_are_idempotent() -> None:
    fake = FakeGitHubClient()
    fake.add_repository(REPOSITORY)
    registry = fake_registry(fake)
    context = execution_context()

    create_issue = registry.get("github.create_issue", "1")
    issue_input = create_issue.input_schema.model_validate(
        {
            "repository": REPOSITORY,
            "title": "Add password recovery",
            "body": "Implement a safe reset flow.",
            "idempotency_key": "password-recovery-001",
        }
    )
    first = create_issue.handler.execute(context, issue_input)
    second = create_issue.handler.execute(context, issue_input)
    assert first.number == second.number == 1
    assert len(fake.issues[REPOSITORY]) == 1

    create_branch = registry.get("github.create_branch", "1")
    branch_input = create_branch.input_schema.model_validate(
        {
            "repository": REPOSITORY,
            "branch": "feature/password-recovery",
            "from_ref": "main",
        }
    )
    branch = create_branch.handler.execute(context, branch_input)
    assert branch.branch == "feature/password-recovery"

    write_file = registry.get("github.create_or_update_file", "1")
    file_input = write_file.input_schema.model_validate(
        {
            "repository": REPOSITORY,
            "path": "README.md",
            "branch": "feature/password-recovery",
            "content": "UTF-8 documentation",
            "message": "docs: describe password recovery",
        }
    )
    written = write_file.handler.execute(context, file_input)
    assert written.created is True

    open_pr = registry.get("github.open_pull_request", "1")
    pr_input = open_pr.input_schema.model_validate(
        {
            "repository": REPOSITORY,
            "head": "feature/password-recovery",
            "base": "main",
            "title": "docs: describe password recovery",
            "body": "Documents the proposed flow.",
        }
    )
    first_pr = open_pr.handler.execute(context, pr_input)
    second_pr = open_pr.handler.execute(context, pr_input)
    assert first_pr.number == second_pr.number == 1
    assert second_pr.already_existed is True


@pytest.mark.parametrize(
    ("status", "headers", "error_type"),
    [
        (401, {}, GitHubAuthenticationError),
        (403, {}, GitHubPermissionError),
        (404, {}, GitHubNotFoundError),
        (429, {"Retry-After": "10"}, GitHubRateLimitError),
        (503, {}, GitHubTransientError),
    ],
)
def test_http_client_maps_safe_errors(
    status: int, headers: dict[str, str], error_type: type[Exception]
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-token"
        return httpx.Response(status, headers=headers, json={"message": "raw-secret-detail"})

    client = HttpGitHubClient(
        GitHubClientConfig(token="test-token", timeout_seconds=1),
        transport=httpx.MockTransport(respond),
    )
    with pytest.raises(error_type) as captured:
        client.get_repository(REPOSITORY)
    assert "raw-secret-detail" not in str(captured.value)


def test_http_client_timeout_invalid_payload_and_rate_metadata() -> None:
    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret timeout detail")

    client = HttpGitHubClient(
        GitHubClientConfig(token="test-token", timeout_seconds=1),
        transport=httpx.MockTransport(timeout),
    )
    with pytest.raises(GitHubTimeoutError):
        client.get_repository(REPOSITORY)

    def invalid(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    client = HttpGitHubClient(
        GitHubClientConfig(token="test-token", timeout_seconds=1),
        transport=httpx.MockTransport(invalid),
    )
    with pytest.raises(GitHubValidationError):
        client.get_repository(REPOSITORY)

    def success(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"X-RateLimit-Remaining": "42", "X-RateLimit-Reset": "0"},
            json={
                "name": "Agent",
                "full_name": REPOSITORY,
                "description": None,
                "default_branch": "main",
                "private": False,
                "html_url": f"https://github.com/{REPOSITORY}",
                "url": f"https://api.github.com/repos/{REPOSITORY}",
            },
        )

    client = HttpGitHubClient(
        GitHubClientConfig(token="test-token", timeout_seconds=1),
        transport=httpx.MockTransport(success),
    )
    assert client.get_repository(REPOSITORY)["name"] == "Agent"
    assert client.rate_limit is not None
    assert client.rate_limit.remaining == 42


def _ready_development_task(
    client: TestClient, db_session: Session
) -> tuple[dict[str, str], dict[str, object]]:
    db_session.add_all(
        [
            Agent(id="supervisor", name="Supervisor", description="Coordination"),
            Agent(id="development", name="Development", description="Engineering"),
        ]
    )
    db_session.commit()
    auth = client.post(
        "/api/v1/auth/register",
        json={
            "email": "github-approval@example.com",
            "password": PASSWORD,
            "full_name": "GitHub Owner",
        },
    ).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    command = client.post(
        "/api/v1/commands", headers=headers, json={"input": "Create a GitHub issue"}
    ).json()
    plan = client.post(
        f"/api/v1/commands/{command['id']}/plan",
        headers=headers,
        json={"title": "GitHub plan", "objective": "Create an approved issue"},
    ).json()
    task = client.post(
        f"/api/v1/plans/{plan['id']}/tasks",
        headers=headers,
        json={
            "agent_id": "development",
            "title": "Create issue",
            "instructions": "Propose one issue.",
            "priority": "normal",
            "risk_level": "green",
            "sequence": 1,
        },
    ).json()
    client.post(f"/api/v1/plans/{plan['id']}/approve", headers=headers)
    return headers, task


def test_github_create_issue_waits_for_approval(client: TestClient, db_session: Session) -> None:
    headers, task = _ready_development_task(client, db_session)
    action = client.post(
        f"/api/v1/tasks/{task['id']}/actions",
        headers=headers,
        json={
            "tool_name": "github.create_issue",
            "input_payload": {
                "repository": REPOSITORY,
                "title": "Add password recovery",
                "body": "Implement a reset flow.",
            },
        },
    )
    assert action.status_code == 201
    dispatched = client.post(f"/api/v1/actions/{action.json()['id']}/dispatch", headers=headers)
    assert dispatched.status_code == 200
    assert dispatched.json()["execution"] is None
    assert dispatched.json()["approval"]["status"] == "pending"
    assert dispatched.json()["action"]["risk_level"] == "yellow"


def test_github_status_never_returns_token(client: TestClient, db_session: Session) -> None:
    headers, _task = _ready_development_task(client, db_session)
    response = client.get("/api/v1/integrations/github/status", headers=headers)
    assert response.status_code == 200
    assert set(response.json()) == {
        "enabled",
        "allowed_repositories",
        "credential_configured",
    }
    assert "token" not in json.dumps(response.json()).lower()


def test_schema_rejects_arbitrary_fields() -> None:
    fake = FakeGitHubClient()
    schema = fake_registry(fake).get("github.get_repository", "1").input_schema
    with pytest.raises(ValidationError):
        schema.model_validate({"repository": REPOSITORY, "arbitrary": "value"})


def _agent_outcome(tool_name: str, input_payload: dict[str, object]):
    from app.ai.base import LLMResult
    from app.schemas.specialized_agent import AgentActionProposal, AgentProposal

    return LLMResult(
        data=AgentProposal(
            summary="Prepared a governed GitHub action",
            actions=[
                AgentActionProposal(
                    tool_name=tool_name,
                    input_payload=input_payload,
                    reason="The task requires repository evidence or a governed write",
                    expected_outcome="A verified GitHub result",
                    risk_level=RiskLevel.GREEN,
                    sequence=1,
                )
            ],
        ),
        provider="fake",
        model="fake-development-v2",
        input_tokens=10,
        output_tokens=10,
        total_tokens=20,
        latency_ms=1,
    )


def test_development_v2_is_only_agent_with_github_capabilities() -> None:
    from app.agents.registry import build_agent_registry

    agents = {agent.agent_id: agent for agent in build_agent_registry().list()}
    development = agents["development"]
    assert development.prompt_version == "development-v2"
    assert development.allowed_tools >= READ_TOOLS | WRITE_TOOLS
    for agent_id in {"marketing", "sales", "support"}:
        assert not (agents[agent_id].allowed_tools & (READ_TOOLS | WRITE_TOOLS))


def test_development_agent_write_auto_dispatches_to_approval_only(
    client: TestClient, db_session: Session
) -> None:
    from sqlalchemy import select

    from app.agents.runner import AgentRunnerService
    from app.models.approval_request import ApprovalRequest
    from app.models.user import User
    from app.models.workflow_enums import TaskActionStatus
    from tests.fakes import FakeLLMProvider

    _headers, task = _ready_development_task(client, db_session)
    user = db_session.scalar(select(User).where(User.email == "github-approval@example.com"))
    assert user is not None
    fake = FakeGitHubClient()
    fake.add_repository(REPOSITORY)
    registry = fake_registry(fake)
    provider = FakeLLMProvider(
        [
            _agent_outcome(
                "github.create_issue",
                {
                    "repository": REPOSITORY,
                    "title": "Add password recovery",
                    "body": "Implement a safe reset flow.",
                },
            )
        ]
    )

    result = AgentRunnerService(
        db_session,
        provider,
        settings=github_settings(),
        tool_registry=registry,
    ).run(UUID(task["id"]), user.id)

    assert result.actions[0].status == TaskActionStatus.WAITING_APPROVAL
    assert db_session.query(ApprovalRequest).count() == 1
    assert fake.issues[REPOSITORY] == []


def test_green_github_read_auto_executes_through_worker(
    client: TestClient, db_session: Session
) -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app.agents.runner import AgentRunnerService
    from app.execution.policies import RetryPolicy
    from app.execution.worker import ExecutionWorker
    from app.models.audit_log import AuditLog
    from app.models.task_execution import TaskExecution
    from app.models.user import User
    from app.models.workflow_enums import TaskActionStatus, TaskExecutionStatus
    from tests.fakes import FakeLLMProvider

    _headers, task = _ready_development_task(client, db_session)
    user = db_session.scalar(select(User).where(User.email == "github-approval@example.com"))
    assert user is not None
    fake = FakeGitHubClient()
    fake.add_repository(REPOSITORY)
    fake.add_file(REPOSITORY, "README.md", "Trusted only as external data.")
    registry = fake_registry(fake)
    provider = FakeLLMProvider(
        [
            _agent_outcome(
                "github.read_file",
                {"repository": REPOSITORY, "path": "README.md", "ref": "main"},
            )
        ]
    )
    result = AgentRunnerService(
        db_session,
        provider,
        settings=github_settings(),
        tool_registry=registry,
    ).run(UUID(task["id"]), user.id)
    assert result.actions[0].status == TaskActionStatus.QUEUED
    execution = db_session.scalar(select(TaskExecution))
    assert execution.status == TaskExecutionStatus.QUEUED

    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    completed = ExecutionWorker(
        factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
        credential_provider=StaticCredentialProvider(),
    ).execute(execution.id)

    assert completed.status == TaskExecutionStatus.SUCCEEDED
    assert completed.output_payload["trust"] == "untrusted"
    assert db_session.scalar(select(AuditLog).where(AuditLog.event_type == "github_file_read"))


def test_every_github_tool_accepts_valid_schema_and_returns_safe_output() -> None:
    from pydantic import BaseModel

    fake = FakeGitHubClient()
    fake.add_repository(REPOSITORY)
    fake.add_file(REPOSITORY, "README.md", "External repository content")
    fake.create_issue(REPOSITORY, "Existing issue", "Body", None)
    fake.create_branch(REPOSITORY, "feature/existing", "main")
    fake.open_pull_request(
        REPOSITORY,
        "feature/existing",
        "main",
        "Existing pull request",
        "Body",
    )
    registry = fake_registry(fake)
    context = execution_context()
    payloads: dict[str, dict[str, object]] = {
        "github.get_repository": {"repository": REPOSITORY},
        "github.list_branches": {"repository": REPOSITORY, "limit": 20},
        "github.read_file": {
            "repository": REPOSITORY,
            "path": "README.md",
            "ref": "main",
        },
        "github.list_pull_requests": {"repository": REPOSITORY, "state": "open"},
        "github.get_pull_request": {"repository": REPOSITORY, "number": 1},
        "github.list_issues": {"repository": REPOSITORY, "state": "open"},
        "github.get_issue": {"repository": REPOSITORY, "number": 1},
        "github.create_issue": {
            "repository": REPOSITORY,
            "title": "New issue",
            "body": "Body",
        },
        "github.comment_issue": {
            "repository": REPOSITORY,
            "number": 1,
            "body": "A reviewed comment",
        },
        "github.create_branch": {
            "repository": REPOSITORY,
            "branch": "feature/new-safe-branch",
            "from_ref": "main",
        },
        "github.create_or_update_file": {
            "repository": REPOSITORY,
            "path": "docs/new.md",
            "branch": "feature/new-safe-branch",
            "content": "Safe UTF-8 content",
            "message": "docs: add safe content",
        },
        "github.open_pull_request": {
            "repository": REPOSITORY,
            "head": "feature/new-safe-branch",
            "base": "main",
            "title": "docs: add safe content",
            "body": "Body",
        },
    }

    for name, raw_payload in payloads.items():
        definition = registry.get(name, "1")
        payload = registry.validate_input(definition, raw_payload, "development")
        output = definition.handler.execute(context, payload)
        assert isinstance(output, BaseModel)
        assert "test-token" not in output.model_dump_json()
        assert definition.input_schema.model_config["extra"] == "forbid"
        if name in READ_TOOLS:
            assert output.external_content is True
            assert output.trust == "untrusted"


def test_github_token_is_redacted_in_settings_repr() -> None:
    settings = github_settings(github_token="sensitive-token-value")
    assert "sensitive-token-value" not in repr(settings)
    assert "**********" in repr(settings)
