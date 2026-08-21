import base64
from copy import deepcopy
from typing import Any

from app.integrations.github.errors import GitHubNotFoundError, GitHubValidationError
from app.integrations.github.schemas import RateLimitMetadata


class FakeGitHubClient:
    def __init__(self) -> None:
        self.rate_limit = RateLimitMetadata(remaining=5000, reset_at=None)
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.repositories: dict[str, dict[str, Any]] = {}
        self.branches: dict[str, dict[str, str]] = {}
        self.files: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.issues: dict[str, list[dict[str, Any]]] = {}
        self.comments: dict[tuple[str, int], list[dict[str, Any]]] = {}
        self.pull_requests: dict[str, list[dict[str, Any]]] = {}

    def close(self) -> None:
        self._record("close")

    def add_repository(
        self,
        repository: str,
        *,
        description: str = "Test repository",
        default_branch: str = "main",
        private: bool = False,
    ) -> None:
        owner, name = repository.split("/", 1)
        self.repositories[repository] = {
            "name": name,
            "full_name": repository,
            "description": description,
            "default_branch": default_branch,
            "private": private,
            "html_url": f"https://github.com/{repository}",
            "url": f"https://api.github.com/repos/{repository}",
            "owner": {"login": owner},
        }
        self.branches[repository] = {default_branch: "a" * 40}
        self.issues[repository] = []
        self.pull_requests[repository] = []

    def add_file(
        self, repository: str, path: str, content: str, *, ref: str = "main", sha: str = "b" * 40
    ) -> None:
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        self.files[(repository, path, ref)] = {
            "type": "file",
            "path": path,
            "sha": sha,
            "size": len(content.encode("utf-8")),
            "encoding": "base64",
            "content": encoded,
        }

    def _record(self, name: str, **payload: object) -> None:
        self.calls.append((name, payload))

    def _repository(self, repository: str) -> None:
        if repository not in self.repositories:
            raise GitHubNotFoundError("GitHub resource was not found")

    def get_repository(self, repository: str) -> dict[str, Any]:
        self._record("get_repository", repository=repository)
        self._repository(repository)
        return deepcopy(self.repositories[repository])

    def list_branches(self, repository: str, limit: int) -> list[dict[str, Any]]:
        self._record("list_branches", repository=repository, limit=limit)
        self._repository(repository)
        return [
            {"name": name, "commit": {"sha": sha}, "protected": name == "main"}
            for name, sha in list(self.branches[repository].items())[:limit]
        ]

    def read_file(self, repository: str, path: str, ref: str) -> dict[str, Any]:
        self._record("read_file", repository=repository, path=path, ref=ref)
        self._repository(repository)
        try:
            return deepcopy(self.files[(repository, path, ref)])
        except KeyError as error:
            raise GitHubNotFoundError("GitHub resource was not found") from error

    def list_pull_requests(self, repository: str, state: str, limit: int) -> list[dict[str, Any]]:
        self._record("list_pull_requests", repository=repository, state=state, limit=limit)
        self._repository(repository)
        values = self.pull_requests[repository]
        return deepcopy(
            [item for item in values if state == "all" or item["state"] == state][:limit]
        )

    def get_pull_request(self, repository: str, number: int) -> dict[str, Any]:
        self._record("get_pull_request", repository=repository, number=number)
        for item in self.pull_requests.get(repository, []):
            if item["number"] == number:
                return deepcopy(item)
        raise GitHubNotFoundError("GitHub resource was not found")

    def list_issues(self, repository: str, state: str, limit: int) -> list[dict[str, Any]]:
        self._record("list_issues", repository=repository, state=state, limit=limit)
        self._repository(repository)
        values = self.issues[repository]
        return deepcopy(
            [item for item in values if state == "all" or item["state"] == state][:limit]
        )

    def get_issue(self, repository: str, number: int) -> dict[str, Any]:
        self._record("get_issue", repository=repository, number=number)
        for item in self.issues.get(repository, []):
            if item["number"] == number:
                return deepcopy(item)
        raise GitHubNotFoundError("GitHub resource was not found")

    def create_issue(
        self, repository: str, title: str, body: str, idempotency_key: str | None
    ) -> dict[str, Any]:
        self._record(
            "create_issue",
            repository=repository,
            title=title,
            body=body,
            idempotency_key=idempotency_key,
        )
        self._repository(repository)
        if idempotency_key:
            for item in self.issues[repository]:
                if item.get("_idempotency_key") == idempotency_key:
                    return deepcopy(item | {"_already_existed": True})
        number = len(self.issues[repository]) + 1
        issue = {
            "number": number,
            "title": title,
            "body": body,
            "state": "open",
            "html_url": f"https://github.com/{repository}/issues/{number}",
            "_idempotency_key": idempotency_key,
        }
        self.issues[repository].append(issue)
        return deepcopy(issue)

    def comment_issue(
        self, repository: str, number: int, body: str, idempotency_key: str | None
    ) -> dict[str, Any]:
        self._record(
            "comment_issue",
            repository=repository,
            number=number,
            body=body,
            idempotency_key=idempotency_key,
        )
        self.get_issue(repository, number)
        values = self.comments.setdefault((repository, number), [])
        if idempotency_key:
            for item in values:
                if item.get("_idempotency_key") == idempotency_key:
                    return deepcopy(item | {"_already_existed": True})
        comment_id = len(values) + 1
        comment = {
            "id": comment_id,
            "body": body,
            "html_url": f"https://github.com/{repository}/issues/{number}#issuecomment-{comment_id}",
            "_idempotency_key": idempotency_key,
        }
        values.append(comment)
        return deepcopy(comment)

    def create_branch(self, repository: str, branch: str, from_ref: str) -> dict[str, Any]:
        self._record("create_branch", repository=repository, branch=branch, from_ref=from_ref)
        self._repository(repository)
        try:
            source_sha = self.branches[repository][from_ref]
        except KeyError as error:
            raise GitHubNotFoundError("GitHub resource was not found") from error
        existing = self.branches[repository].get(branch)
        if existing and existing != source_sha:
            raise GitHubValidationError("Branch already exists at a different commit")
        self.branches[repository][branch] = source_sha
        return {
            "ref": f"refs/heads/{branch}",
            "object": {"sha": source_sha},
            "_already_existed": existing is not None,
        }

    def create_or_update_file(
        self,
        repository: str,
        path: str,
        branch: str,
        content: str,
        message: str,
        expected_sha: str | None,
    ) -> dict[str, Any]:
        self._record(
            "create_or_update_file",
            repository=repository,
            path=path,
            branch=branch,
            message=message,
            expected_sha=expected_sha,
        )
        self._repository(repository)
        if branch not in self.branches[repository]:
            raise GitHubNotFoundError("GitHub resource was not found")
        current = self.files.get((repository, path, branch))
        current_sha = current["sha"] if current else None
        if expected_sha is not None and expected_sha != current_sha:
            raise GitHubValidationError("File changed since the expected SHA")
        new_sha = f"{len(self.files) + 1:040x}"
        self.add_file(repository, path, content, ref=branch, sha=new_sha)
        return {
            "content": {"sha": new_sha},
            "commit": {"sha": f"{len(self.files) + 100:040x}"},
            "_created": current is None,
        }

    def open_pull_request(
        self, repository: str, head: str, base: str, title: str, body: str
    ) -> dict[str, Any]:
        self._record(
            "open_pull_request",
            repository=repository,
            head=head,
            base=base,
            title=title,
            body=body,
        )
        self._repository(repository)
        for item in self.pull_requests[repository]:
            if (
                item["state"] == "open"
                and item["head"]["ref"] == head
                and item["base"]["ref"] == base
            ):
                return deepcopy(item | {"_already_existed": True})
        number = len(self.pull_requests[repository]) + 1
        pull = {
            "number": number,
            "title": title,
            "body": body,
            "state": "open",
            "draft": False,
            "merged": False,
            "head": {"ref": head},
            "base": {"ref": base},
            "html_url": f"https://github.com/{repository}/pull/{number}",
        }
        self.pull_requests[repository].append(pull)
        return deepcopy(pull)
