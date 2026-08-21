from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GitHubSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GitHubRepositoryInput(GitHubSchema):
    repository: str = Field(min_length=3, max_length=200)


class GitHubListBranchesInput(GitHubRepositoryInput):
    limit: int = Field(default=50, ge=1, le=100)


class GitHubReadFileInput(GitHubRepositoryInput):
    path: str = Field(min_length=1, max_length=1000)
    ref: str = Field(default="main", min_length=1, max_length=200)


class GitHubListPullRequestsInput(GitHubRepositoryInput):
    state: Literal["open", "closed", "all"] = "open"
    limit: int = Field(default=30, ge=1, le=100)


class GitHubGetPullRequestInput(GitHubRepositoryInput):
    number: int = Field(ge=1)


class GitHubListIssuesInput(GitHubRepositoryInput):
    state: Literal["open", "closed", "all"] = "open"
    limit: int = Field(default=30, ge=1, le=100)


class GitHubGetIssueInput(GitHubRepositoryInput):
    number: int = Field(ge=1)


class GitHubCreateIssueInput(GitHubRepositoryInput):
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=50_000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class GitHubCommentIssueInput(GitHubRepositoryInput):
    number: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=50_000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class GitHubCreateBranchInput(GitHubRepositoryInput):
    branch: str = Field(min_length=1, max_length=200)
    from_ref: str = Field(default="main", min_length=1, max_length=200)


class GitHubCreateOrUpdateFileInput(GitHubRepositoryInput):
    path: str = Field(min_length=1, max_length=1000)
    branch: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=1_000_000)
    message: str = Field(min_length=1, max_length=500)
    expected_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class GitHubOpenPullRequestInput(GitHubRepositoryInput):
    head: str = Field(min_length=1, max_length=200)
    base: str = Field(default="main", min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=50_000)


class RateLimitMetadata(GitHubSchema):
    remaining: int | None = None
    reset_at: str | None = None


class GitHubRepositoryOutput(GitHubSchema):
    name: str
    full_name: str
    description: str | None
    default_branch: str
    private: bool
    html_url: str
    api_url: str
    rate_limit: RateLimitMetadata | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class GitHubBranch(GitHubSchema):
    name: str
    sha: str
    protected: bool


class GitHubBranchesOutput(GitHubSchema):
    repository: str
    branches: list[GitHubBranch]
    rate_limit: RateLimitMetadata | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class GitHubFileOutput(GitHubSchema):
    repository: str
    path: str
    ref: str
    sha: str
    size: int
    content: str
    truncated: bool
    encoding: Literal["utf-8"] = "utf-8"
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"
    rate_limit: RateLimitMetadata | None = None


class GitHubPullRequest(GitHubSchema):
    number: int
    title: str
    state: str
    head: str
    base: str
    html_url: str
    body: str | None = None
    draft: bool = False


class GitHubPullRequestsOutput(GitHubSchema):
    repository: str
    pull_requests: list[GitHubPullRequest]
    rate_limit: RateLimitMetadata | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class GitHubPullRequestOutput(GitHubPullRequest):
    repository: str
    merged: bool = False
    rate_limit: RateLimitMetadata | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class GitHubIssue(GitHubSchema):
    number: int
    title: str
    state: str
    html_url: str
    body: str | None = None


class GitHubIssuesOutput(GitHubSchema):
    repository: str
    issues: list[GitHubIssue]
    rate_limit: RateLimitMetadata | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class GitHubIssueOutput(GitHubIssue):
    repository: str
    rate_limit: RateLimitMetadata | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class GitHubCommentOutput(GitHubSchema):
    repository: str
    issue_number: int
    comment_id: int
    html_url: str
    rate_limit: RateLimitMetadata | None = None


class GitHubBranchOutput(GitHubSchema):
    repository: str
    branch: str
    sha: str
    already_existed: bool = False
    rate_limit: RateLimitMetadata | None = None


class GitHubFileWriteOutput(GitHubSchema):
    repository: str
    path: str
    branch: str
    sha: str
    commit_sha: str
    created: bool
    rate_limit: RateLimitMetadata | None = None


class GitHubPullRequestWriteOutput(GitHubSchema):
    repository: str
    number: int
    html_url: str
    head: str
    base: str
    already_existed: bool = False
    rate_limit: RateLimitMetadata | None = None
