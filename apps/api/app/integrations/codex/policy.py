from pathlib import PurePosixPath

from app.integrations.codex.errors import CodexPolicyError
from app.integrations.github.policy import RepositoryAccessPolicy

FORBIDDEN_NAMES = {
    ".git",
    ".env",
    ".env.local",
    ".npmrc",
    ".pypirc",
    "auth.json",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".jks")


class CodexRepositoryPolicy:
    def __init__(
        self,
        allowed_repositories: list[str],
        protected_branches: list[str],
        allowed_branch_prefixes: list[str],
    ) -> None:
        self.repositories = RepositoryAccessPolicy(
            allowed_repositories,
            protected_branches,
            allowed_branch_prefixes,
        )

    def authorize_repository(self, repository: str) -> str:
        return self.repositories.authorize(repository, "get_repository")

    def validate_base_branch(self, branch: str) -> str:
        return self.repositories.validate_branch(branch)

    def validate_working_branch(self, branch: str) -> str:
        if branch.strip().casefold() in {"main", "master", "production"}:
            raise CodexPolicyError("Codex cannot target a primary or production branch")
        return self.repositories.validate_branch(branch, write_target=True)

    def validate_allowed_paths(self, paths: list[str]) -> list[str]:
        normalized: list[str] = []
        for path in paths:
            candidate = self.validate_changed_path(path.rstrip("/"))
            normalized.append(candidate)
        return normalized

    def validate_changed_path(self, path: str) -> str:
        if not path or "\\" in path or path.startswith("/"):
            raise CodexPolicyError("Codex changed an invalid repository path")
        parts = PurePosixPath(path).parts
        lowered = [part.casefold() for part in parts]
        if any(part in {"", ".", ".."} for part in parts):
            raise CodexPolicyError("Codex path traversal is not allowed")
        if any(part in FORBIDDEN_NAMES or part.startswith(".env.") for part in lowered):
            raise CodexPolicyError("Codex cannot modify credential or repository metadata paths")
        if any(path.casefold().endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            raise CodexPolicyError("Codex cannot modify key or credential files")
        return "/".join(parts)

    def validate_changed_files(self, files: list[str], allowed_paths: list[str]) -> list[str]:
        allowed = self.validate_allowed_paths(allowed_paths)
        normalized = [self.validate_changed_path(path) for path in files]
        if allowed:
            for path in normalized:
                if not any(path == root or path.startswith(f"{root}/") for root in allowed):
                    raise CodexPolicyError("Codex changed a path outside the approved scope")
        return normalized
