import base64
import binascii
from typing import Any

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.execution.context import ExecutionContext
from app.execution.registry import ToolDefinition
from app.integrations.github.client import (
    GitHubClient,
    GitHubClientFactory,
    build_github_client,
)
from app.integrations.github.errors import GitHubValidationError
from app.integrations.github.policy import RepositoryAccessPolicy
from app.integrations.github.schemas import (
    GitHubBranch,
    GitHubBranchesOutput,
    GitHubBranchOutput,
    GitHubCommentIssueInput,
    GitHubCommentOutput,
    GitHubCreateBranchInput,
    GitHubCreateIssueInput,
    GitHubCreateOrUpdateFileInput,
    GitHubFileOutput,
    GitHubFileWriteOutput,
    GitHubGetIssueInput,
    GitHubGetPullRequestInput,
    GitHubIssue,
    GitHubIssueOutput,
    GitHubIssuesOutput,
    GitHubListBranchesInput,
    GitHubListIssuesInput,
    GitHubListPullRequestsInput,
    GitHubOpenPullRequestInput,
    GitHubPullRequest,
    GitHubPullRequestOutput,
    GitHubPullRequestsOutput,
    GitHubPullRequestWriteOutput,
    GitHubReadFileInput,
    GitHubRepositoryInput,
    GitHubRepositoryOutput,
)
from app.models.workflow_enums import RiskLevel


class GitHubToolHandler:
    def __init__(
        self,
        operation: str,
        *,
        settings: Settings | None = None,
        client_factory: GitHubClientFactory = build_github_client,
    ) -> None:
        self.operation = operation
        self.settings = settings or get_settings()
        self.client_factory = client_factory
        self.policy = RepositoryAccessPolicy(
            self.settings.github_allowed_repository_list,
            self.settings.github_protected_branch_list,
            self.settings.github_allowed_branch_prefix_list,
        )

    def execute(self, context: ExecutionContext, payload: BaseModel) -> BaseModel:
        repository = self.policy.authorize(str(payload.repository), self.operation)
        if not self.settings.github_integration_enabled:
            raise GitHubValidationError("GitHub integration is disabled")
        credential = context.credentials.resolve("github")
        client = self.client_factory(
            credential.access_token, self.settings.github_api_timeout_seconds
        )
        try:
            method = getattr(self, f"_execute_{self.operation}")
            return method(client, repository, payload)
        finally:
            client.close()

    def _execute_get_repository(
        self, client: GitHubClient, repository: str, _payload: BaseModel
    ) -> BaseModel:
        value = client.get_repository(repository)
        return GitHubRepositoryOutput(
            name=str(value["name"]),
            full_name=str(value["full_name"]),
            description=_optional_text(
                value.get("description"), self.settings.github_max_output_chars
            ),
            default_branch=str(value["default_branch"]),
            private=bool(value["private"]),
            html_url=_safe_url(value["html_url"], api=False),
            api_url=_safe_url(value["url"], api=True),
            rate_limit=client.rate_limit,
        )

    def _execute_list_branches(
        self, client: GitHubClient, repository: str, payload: GitHubListBranchesInput
    ) -> BaseModel:
        values = client.list_branches(repository, payload.limit)
        return GitHubBranchesOutput(
            repository=repository,
            branches=[
                GitHubBranch(
                    name=str(item["name"]),
                    sha=str(item["commit"]["sha"]),
                    protected=bool(item.get("protected", False)),
                )
                for item in values
            ],
            rate_limit=client.rate_limit,
        )

    def _execute_read_file(
        self, client: GitHubClient, repository: str, payload: GitHubReadFileInput
    ) -> BaseModel:
        path = self.policy.validate_path(payload.path)
        ref = self.policy.validate_branch(payload.ref)
        value = client.read_file(repository, path, ref)
        if value.get("type") != "file" or value.get("encoding") != "base64":
            raise GitHubValidationError("GitHub path is not a supported file")
        size = int(value.get("size", 0))
        if size > self.settings.github_max_file_bytes:
            raise GitHubValidationError("GitHub file exceeds the configured size limit")
        try:
            raw = base64.b64decode(str(value["content"]), validate=True)
            content = raw.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, KeyError) as error:
            raise GitHubValidationError("GitHub file is binary or invalid") from error
        maximum = self.settings.github_max_output_chars
        return GitHubFileOutput(
            repository=repository,
            path=path,
            ref=ref,
            sha=str(value["sha"]),
            size=size,
            content=content[:maximum],
            truncated=len(content) > maximum,
            rate_limit=client.rate_limit,
        )

    def _execute_list_pull_requests(
        self, client: GitHubClient, repository: str, payload: GitHubListPullRequestsInput
    ) -> BaseModel:
        values = client.list_pull_requests(repository, payload.state, payload.limit)
        return GitHubPullRequestsOutput(
            repository=repository,
            pull_requests=[_pull_request(item, include_body=False) for item in values],
            rate_limit=client.rate_limit,
        )

    def _execute_get_pull_request(
        self, client: GitHubClient, repository: str, payload: GitHubGetPullRequestInput
    ) -> BaseModel:
        value = client.get_pull_request(repository, payload.number)
        parsed = _pull_request(
            value, include_body=True, maximum=self.settings.github_max_output_chars
        )
        return GitHubPullRequestOutput(
            repository=repository,
            merged=bool(value.get("merged", False)),
            rate_limit=client.rate_limit,
            **parsed.model_dump(),
        )

    def _execute_list_issues(
        self, client: GitHubClient, repository: str, payload: GitHubListIssuesInput
    ) -> BaseModel:
        values = client.list_issues(repository, payload.state, payload.limit)
        return GitHubIssuesOutput(
            repository=repository,
            issues=[_issue(item, include_body=False) for item in values],
            rate_limit=client.rate_limit,
        )

    def _execute_get_issue(
        self, client: GitHubClient, repository: str, payload: GitHubGetIssueInput
    ) -> BaseModel:
        value = client.get_issue(repository, payload.number)
        parsed = _issue(value, include_body=True, maximum=self.settings.github_max_output_chars)
        return GitHubIssueOutput(
            repository=repository,
            rate_limit=client.rate_limit,
            **parsed.model_dump(),
        )

    def _execute_create_issue(
        self, client: GitHubClient, repository: str, payload: GitHubCreateIssueInput
    ) -> BaseModel:
        value = client.create_issue(
            repository, payload.title, payload.body, payload.idempotency_key
        )
        parsed = _issue(value, include_body=True, maximum=self.settings.github_max_output_chars)
        return GitHubIssueOutput(
            repository=repository,
            rate_limit=client.rate_limit,
            **parsed.model_dump(),
        )

    def _execute_comment_issue(
        self, client: GitHubClient, repository: str, payload: GitHubCommentIssueInput
    ) -> BaseModel:
        value = client.comment_issue(
            repository, payload.number, payload.body, payload.idempotency_key
        )
        return GitHubCommentOutput(
            repository=repository,
            issue_number=payload.number,
            comment_id=int(value["id"]),
            html_url=_safe_url(value["html_url"], api=False),
            rate_limit=client.rate_limit,
        )

    def _execute_create_branch(
        self, client: GitHubClient, repository: str, payload: GitHubCreateBranchInput
    ) -> BaseModel:
        branch = self.policy.validate_branch(payload.branch, write_target=True)
        source = self.policy.validate_branch(payload.from_ref)
        value = client.create_branch(repository, branch, source)
        return GitHubBranchOutput(
            repository=repository,
            branch=branch,
            sha=str(value["object"]["sha"]),
            already_existed=bool(value.get("_already_existed", False)),
            rate_limit=client.rate_limit,
        )

    def _execute_create_or_update_file(
        self,
        client: GitHubClient,
        repository: str,
        payload: GitHubCreateOrUpdateFileInput,
    ) -> BaseModel:
        path = self.policy.validate_path(payload.path)
        branch = self.policy.validate_branch(payload.branch, write_target=True)
        if len(payload.content.encode("utf-8")) > self.settings.github_max_file_bytes:
            raise GitHubValidationError("GitHub file exceeds the configured size limit")
        value = client.create_or_update_file(
            repository,
            path,
            branch,
            payload.content,
            payload.message,
            payload.expected_sha,
        )
        return GitHubFileWriteOutput(
            repository=repository,
            path=path,
            branch=branch,
            sha=str(value["content"]["sha"]),
            commit_sha=str(value["commit"]["sha"]),
            created=bool(value.get("_created", False)),
            rate_limit=client.rate_limit,
        )

    def _execute_open_pull_request(
        self, client: GitHubClient, repository: str, payload: GitHubOpenPullRequestInput
    ) -> BaseModel:
        head = self.policy.validate_branch(payload.head, write_target=True)
        base = self.policy.validate_branch(payload.base)
        if head == base:
            raise GitHubValidationError("Pull request head and base must differ")
        value = client.open_pull_request(repository, head, base, payload.title, payload.body)
        return GitHubPullRequestWriteOutput(
            repository=repository,
            number=int(value["number"]),
            html_url=_safe_url(value["html_url"], api=False),
            head=str(value["head"]["ref"]),
            base=str(value["base"]["ref"]),
            already_existed=bool(value.get("_already_existed", False)),
            rate_limit=client.rate_limit,
        )


def github_tool_definitions(
    *,
    settings: Settings | None = None,
    client_factory: GitHubClientFactory = build_github_client,
) -> list[ToolDefinition]:
    settings = settings or get_settings()
    specs = (
        ("get_repository", GitHubRepositoryInput, GitHubRepositoryOutput, RiskLevel.GREEN, 2),
        ("list_branches", GitHubListBranchesInput, GitHubBranchesOutput, RiskLevel.GREEN, 2),
        ("read_file", GitHubReadFileInput, GitHubFileOutput, RiskLevel.GREEN, 2),
        (
            "list_pull_requests",
            GitHubListPullRequestsInput,
            GitHubPullRequestsOutput,
            RiskLevel.GREEN,
            2,
        ),
        (
            "get_pull_request",
            GitHubGetPullRequestInput,
            GitHubPullRequestOutput,
            RiskLevel.GREEN,
            2,
        ),
        ("list_issues", GitHubListIssuesInput, GitHubIssuesOutput, RiskLevel.GREEN, 2),
        ("get_issue", GitHubGetIssueInput, GitHubIssueOutput, RiskLevel.GREEN, 2),
        ("create_issue", GitHubCreateIssueInput, GitHubIssueOutput, RiskLevel.YELLOW, 0),
        (
            "comment_issue",
            GitHubCommentIssueInput,
            GitHubCommentOutput,
            RiskLevel.YELLOW,
            0,
        ),
        (
            "create_branch",
            GitHubCreateBranchInput,
            GitHubBranchOutput,
            RiskLevel.YELLOW,
            0,
        ),
        (
            "create_or_update_file",
            GitHubCreateOrUpdateFileInput,
            GitHubFileWriteOutput,
            RiskLevel.YELLOW,
            0,
        ),
        (
            "open_pull_request",
            GitHubOpenPullRequestInput,
            GitHubPullRequestWriteOutput,
            RiskLevel.YELLOW,
            0,
        ),
    )
    definitions = []
    for operation, input_schema, output_schema, risk, retries in specs:
        definitions.append(
            ToolDefinition(
                name=f"github.{operation}",
                version="1",
                description=(
                    f"Perform the allowlisted GitHub {operation.replace('_', ' ')} operation."
                ),
                agent_types=frozenset({"development"}),
                risk_level=risk,
                timeout_seconds=round(settings.github_api_timeout_seconds),
                max_retries=retries,
                requires_approval=risk != RiskLevel.GREEN,
                input_schema=input_schema,
                output_schema=output_schema,
                handler=GitHubToolHandler(
                    operation, settings=settings, client_factory=client_factory
                ),
            )
        )
    return definitions


def _pull_request(
    value: dict[str, Any], *, include_body: bool, maximum: int = 0
) -> GitHubPullRequest:
    body = value.get("body") if include_body else None
    return GitHubPullRequest(
        number=int(value["number"]),
        title=str(value["title"]),
        state=str(value["state"]),
        head=str(value["head"]["ref"]),
        base=str(value["base"]["ref"]),
        html_url=_safe_url(value["html_url"], api=False),
        body=_optional_text(body, maximum) if include_body else None,
        draft=bool(value.get("draft", False)),
    )


def _issue(value: dict[str, Any], *, include_body: bool, maximum: int = 0) -> GitHubIssue:
    body = value.get("body") if include_body else None
    return GitHubIssue(
        number=int(value["number"]),
        title=str(value["title"]),
        state=str(value["state"]),
        html_url=_safe_url(value["html_url"], api=False),
        body=_optional_text(body, maximum) if include_body else None,
    )


def _optional_text(value: object, maximum: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:maximum] if maximum else text


def _safe_url(value: object, *, api: bool) -> str:
    text = str(value)
    prefix = "https://api.github.com/" if api else "https://github.com/"
    if not text.startswith(prefix):
        raise GitHubValidationError("GitHub returned an unsafe URL")
    return text
