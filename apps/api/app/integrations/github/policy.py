import re
from pathlib import PurePosixPath

from app.integrations.github.errors import GitHubPermissionError, GitHubValidationError

REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
KNOWN_SECRET_NAMES = {
    ".env",
    ".env.local",
    ".npmrc",
    ".pypirc",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
}
OPERATIONS = frozenset(
    {
        "get_repository",
        "list_branches",
        "read_file",
        "list_pull_requests",
        "get_pull_request",
        "list_issues",
        "get_issue",
        "create_issue",
        "comment_issue",
        "create_branch",
        "create_or_update_file",
        "open_pull_request",
    }
)


class RepositoryAccessPolicy:
    def __init__(
        self,
        allowed_repositories: list[str],
        protected_branches: list[str],
        allowed_branch_prefixes: list[str],
    ) -> None:
        self.allowed = {item.casefold(): item for item in allowed_repositories}
        self.protected = {item.casefold() for item in protected_branches}
        self.prefixes = tuple(allowed_branch_prefixes)

    def authorize(self, repository: str, operation: str) -> str:
        if operation not in OPERATIONS:
            raise GitHubValidationError("Unsupported GitHub operation")
        if not REPOSITORY_PATTERN.fullmatch(repository):
            raise GitHubValidationError("Repository must use owner/name format")
        canonical = self.allowed.get(repository.casefold())
        if canonical is None:
            raise GitHubPermissionError("Repository is not in the GitHub allowlist")
        return canonical

    def validate_path(self, path: str) -> str:
        if not path or "\\" in path or path.startswith("/"):
            raise GitHubValidationError("GitHub path must be relative")
        parts = PurePosixPath(path).parts
        if any(part in {"", ".", ".."} for part in parts):
            raise GitHubValidationError("GitHub path traversal is not allowed")
        lowered = {part.casefold() for part in parts}
        if lowered & KNOWN_SECRET_NAMES or any(part.startswith(".env.") for part in lowered):
            raise GitHubPermissionError("Reading or writing known secret files is not allowed")
        return "/".join(parts)

    def validate_branch(self, branch: str, *, write_target: bool = False) -> str:
        if (
            not BRANCH_PATTERN.fullmatch(branch)
            or ".." in branch
            or "@{" in branch
            or branch.endswith(("/", ".", ".lock"))
            or "//" in branch
        ):
            raise GitHubValidationError("Invalid GitHub branch name")
        if write_target:
            if branch.casefold() in self.protected:
                raise GitHubPermissionError("Direct writes to protected branches are not allowed")
            if self.prefixes and not branch.startswith(self.prefixes):
                raise GitHubValidationError("Branch does not use an allowed prefix")
        return branch
