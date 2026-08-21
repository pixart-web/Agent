from app.execution.exceptions import ExecutionError


class GitHubError(ExecutionError):
    code = "github_error"


class GitHubAuthenticationError(GitHubError):
    code = "github_authentication_error"


class GitHubPermissionError(GitHubError):
    code = "github_permission_error"


class GitHubNotFoundError(GitHubError):
    code = "github_not_found"


class GitHubRateLimitError(GitHubError):
    code = "github_rate_limit"

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.retryable = retry_after_seconds is not None and retry_after_seconds <= 120


class GitHubTimeoutError(GitHubError):
    code = "github_timeout"
    retryable = True


class GitHubValidationError(GitHubError):
    code = "github_validation_error"


class GitHubTransientError(GitHubError):
    code = "github_transient_error"
    retryable = True
