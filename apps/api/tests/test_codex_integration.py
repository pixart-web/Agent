import json
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.execution.context import ExecutionContext
from app.execution.policies import RetryPolicy
from app.execution.tools.registry import build_tool_registry
from app.execution.worker import ExecutionWorker
from app.integrations.codex.adapter import CodexCLIAdapter
from app.integrations.codex.errors import CodexPolicyError, CodexValidationError
from app.integrations.codex.fake import FakeCodexRunner
from app.integrations.codex.policy import CodexRepositoryPolicy
from app.integrations.codex.schemas import CodexAdapterChangeResult
from app.integrations.credentials import ServiceCredential
from app.models.codex_run import CodexRun
from app.models.user import User
from app.models.workflow_enums import CodexRunStatus, RiskLevel, TaskExecutionStatus
from app.schemas.execution import ApprovalDecision, TaskActionCreate
from app.services.approval_service import ApprovalService
from app.services.execution_service import ExecutionService
from tests.test_github_integration import PASSWORD, REPOSITORY, _ready_development_task


class StaticCredentials:
    def resolve(self, service: str) -> ServiceCredential:
        return ServiceCredential(access_token=f"test-{service}-credential")

    def configured(self, service: str) -> bool:
        return service in {"github", "codex"}


def codex_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_secret_key": "test-only-auth-secret-with-at-least-32-characters",
        "codex_integration_enabled": True,
        "codex_api_key": "test-codex-credential",
        "codex_allowed_repositories": REPOSITORY,
        "github_allowed_repositories": REPOSITORY,
        "github_protected_branches": "main",
        "github_allowed_branch_prefixes": "feature/,fix/,chore/,docs/",
    }
    values.update(overrides)
    return Settings(**values)


def context(run_id=None) -> ExecutionContext:
    return ExecutionContext(
        user_id=uuid4(),
        command_id=uuid4(),
        task_id=uuid4(),
        action_id=uuid4(),
        execution_id=uuid4(),
        correlation_id=uuid4(),
        credentials=StaticCredentials(),
        integration_run_id=run_id or uuid4(),
    )


def test_codex_tool_catalog_has_expected_risk_approval_and_scope() -> None:
    registry = build_tool_registry(settings=codex_settings(), codex_runner=FakeCodexRunner())
    expected = {
        "codex.implement_task": (RiskLevel.YELLOW, True),
        "codex.review_pull_request": (RiskLevel.GREEN, False),
        "codex.fix_pull_request": (RiskLevel.YELLOW, True),
    }
    for name, (risk, approval) in expected.items():
        definition = registry.get(name, "1")
        assert definition.agent_types == frozenset({"development"})
        assert definition.risk_level == risk
        assert definition.requires_approval is approval
        assert definition.max_retries == 0
        assert "token" not in definition.input_schema.model_fields


def test_codex_policy_blocks_primary_branches_secrets_and_path_escape() -> None:
    policy = CodexRepositoryPolicy([REPOSITORY], ["main"], ["feature/", "fix/", "chore/", "docs/"])
    assert policy.validate_working_branch("feature/codex") == "feature/codex"
    for branch in ("main", "master", "production"):
        with pytest.raises(CodexPolicyError):
            policy.validate_working_branch(branch)
    for path in (".env", ".git/config", "secrets/id_rsa", "../outside.py", "cert.pem"):
        with pytest.raises(CodexPolicyError):
            policy.validate_changed_path(path)
    with pytest.raises(CodexPolicyError):
        policy.validate_changed_files(["apps/api/app/main.py"], ["docs"])


def test_cli_adapter_uses_shell_false_bounded_environment_and_removes_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    metadata = tmp_path / "metadata"
    repository.mkdir()
    metadata.mkdir()
    captured: dict[str, object] = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        args = kwargs["args"]
        result_path = Path(args[args.index("--output-last-message") + 1])
        result_path.write_text(json.dumps({"summary": "Safe result"}), encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = CodexCLIAdapter(binary="codex", timeout_seconds=60, max_output_chars=1000).execute(
        prompt="Implement the approved task",
        repository=repository,
        metadata=metadata,
        output_schema=CodexAdapterChangeResult,
        api_key="dedicated-test-key",
        writable=True,
        model=None,
    )
    assert result.result.summary == "Safe result"
    assert captured["shell"] is False
    assert captured["env"]["CODEX_API_KEY"] == "dedicated-test-key"
    assert "GITHUB_TOKEN" not in captured["env"]
    assert 'shell_environment_policy.inherit="core"' in captured["args"]
    assert "shell_environment_policy.ignore_default_excludes=false" in captured["args"]
    assert 'shell_environment_policy.exclude=["CODEX_API_KEY"]' in captured["args"]
    assert "allow_login_shell=false" in captured["args"]
    assert not (metadata / "technical.log").exists()


def test_cli_adapter_rejects_credential_in_structured_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    metadata = tmp_path / "metadata"
    repository.mkdir()
    metadata.mkdir()

    def fake_run(**kwargs):
        args = kwargs["args"]
        Path(args[args.index("--output-last-message") + 1]).write_text(
            json.dumps({"summary": "leaked dedicated-test-key"}), encoding="utf-8"
        )
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(CodexValidationError):
        CodexCLIAdapter(binary="codex", timeout_seconds=60, max_output_chars=1000).execute(
            prompt="Task",
            repository=repository,
            metadata=metadata,
            output_schema=CodexAdapterChangeResult,
            api_key="dedicated-test-key",
            writable=True,
            model=None,
        )


def test_fake_codex_approval_worker_lifecycle_and_ownership(
    client: TestClient, db_session: Session
) -> None:
    headers, task = _ready_development_task(client, db_session)
    user = db_session.scalar(select(User).where(User.email == "github-approval@example.com"))
    assert user is not None
    fake = FakeCodexRunner()
    registry = build_tool_registry(settings=codex_settings(), codex_runner=fake)
    service = ExecutionService(db_session, registry)
    action = service.create_action(
        UUID(task["id"]),
        user.id,
        TaskActionCreate(
            tool_name="codex.implement_task",
            input_payload={
                "repository": REPOSITORY,
                "base_branch": "main",
                "working_branch": "feature/fake-codex",
                "title": "Document fake Codex",
                "instructions": "Update the approved documentation only.",
                "acceptance_criteria": ["Documentation is updated"],
                "allowed_paths": ["docs"],
            },
        ),
    )
    dispatched = service.dispatch(action.id, user.id)
    assert dispatched.approval is not None
    assert "create one commit" in dispatched.approval.description
    approval, execution = ApprovalService(db_session).approve(
        dispatched.approval.id, user.id, ApprovalDecision()
    )
    assert approval.status.value == "approved"

    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    completed = ExecutionWorker(
        factory,
        registry=registry,
        retry_policy=RetryPolicy(system_max_retries=3, jitter_ratio=0),
        credential_provider=StaticCredentials(),
    ).execute(execution.id)
    assert completed is not None and completed.status == TaskExecutionStatus.SUCCEEDED
    db_session.expire_all()
    run = db_session.scalar(select(CodexRun).where(CodexRun.task_action_id == action.id))
    assert run is not None
    assert run.status == CodexRunStatus.SUCCEEDED
    assert run.commit_sha == "a" * 40
    assert run.tests_passed is True
    assert client.get(f"/api/v1/codex/runs/{run.id}", headers=headers).status_code == 200

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-codex@example.com",
            "password": PASSWORD,
            "full_name": "Other Owner",
        },
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/v1/codex/runs/{run.id}", headers=other_headers).status_code == 404
