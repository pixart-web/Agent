import base64
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from app.integrations.github.errors import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubTimeoutError,
    GitHubTransientError,
    GitHubValidationError,
)
from app.integrations.github.schemas import RateLimitMetadata

JsonObject = dict[str, Any]


class GitHubClient(Protocol):
    rate_limit: RateLimitMetadata | None

    def close(self) -> None: ...
    def get_repository(self, repository: str) -> JsonObject: ...
    def list_branches(self, repository: str, limit: int) -> list[JsonObject]: ...
    def read_file(self, repository: str, path: str, ref: str) -> JsonObject: ...
    def list_pull_requests(self, repository: str, state: str, limit: int) -> list[JsonObject]: ...
    def get_pull_request(self, repository: str, number: int) -> JsonObject: ...
    def list_issues(self, repository: str, state: str, limit: int) -> list[JsonObject]: ...
    def get_issue(self, repository: str, number: int) -> JsonObject: ...
    def create_issue(
        self, repository: str, title: str, body: str, idempotency_key: str | None
    ) -> JsonObject: ...
    def comment_issue(
        self, repository: str, number: int, body: str, idempotency_key: str | None
    ) -> JsonObject: ...
    def create_branch(self, repository: str, branch: str, from_ref: str) -> JsonObject: ...
    def create_or_update_file(
        self,
        repository: str,
        path: str,
        branch: str,
        content: str,
        message: str,
        expected_sha: str | None,
    ) -> JsonObject: ...
    def open_pull_request(
        self, repository: str, head: str, base: str, title: str, body: str
    ) -> JsonObject: ...


@dataclass(frozen=True)
class GitHubClientConfig:
    token: str
    timeout_seconds: float


class HttpGitHubClient:
    def __init__(
        self,
        config: GitHubClientConfig,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.client = httpx.Client(
            base_url="https://api.github.com",
            timeout=config.timeout_seconds,
            transport=transport,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {config.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Kiko-Agent",
            },
        )
        self.rate_limit: RateLimitMetadata | None = None

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise GitHubTimeoutError("GitHub request timed out") from error
        except httpx.TransportError as error:
            raise GitHubTransientError("GitHub is temporarily unavailable") from error
        self.rate_limit = self._rate_limit(response)
        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return {}
            try:
                return response.json()
            except ValueError as error:
                raise GitHubValidationError("GitHub returned an invalid response") from error
        self._raise_response_error(response)

    @staticmethod
    def _rate_limit(response: httpx.Response) -> RateLimitMetadata:
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        reset_at = None
        if reset and reset.isdigit():
            reset_at = datetime.fromtimestamp(int(reset), tz=UTC).isoformat()
        return RateLimitMetadata(
            remaining=int(remaining) if remaining and remaining.isdigit() else None,
            reset_at=reset_at,
        )

    @staticmethod
    def _raise_response_error(response: httpx.Response) -> None:
        status = response.status_code
        if status == 401:
            raise GitHubAuthenticationError("GitHub authentication failed")
        if status == 403 and response.headers.get("x-ratelimit-remaining") == "0":
            retry_after = _retry_after(response)
            raise GitHubRateLimitError(
                "GitHub rate limit exceeded", retry_after_seconds=retry_after
            )
        if status == 403:
            raise GitHubPermissionError("GitHub denied this operation")
        if status == 404:
            raise GitHubNotFoundError("GitHub resource was not found")
        if status == 429:
            raise GitHubRateLimitError(
                "GitHub rate limit exceeded", retry_after_seconds=_retry_after(response)
            )
        if status in {502, 503, 504}:
            raise GitHubTransientError("GitHub is temporarily unavailable")
        if status in {409, 422}:
            raise GitHubValidationError("GitHub rejected the operation")
        raise GitHubValidationError(f"GitHub request failed with status {status}")

    def get_repository(self, repository: str) -> JsonObject:
        return self._request("GET", f"/repos/{repository}")

    def list_branches(self, repository: str, limit: int) -> list[JsonObject]:
        return self._request("GET", f"/repos/{repository}/branches", params={"per_page": limit})

    def read_file(self, repository: str, path: str, ref: str) -> JsonObject:
        safe_path = quote(path, safe="/")
        return self._request(
            "GET", f"/repos/{repository}/contents/{safe_path}", params={"ref": ref}
        )

    def list_pull_requests(self, repository: str, state: str, limit: int) -> list[JsonObject]:
        return self._request(
            "GET", f"/repos/{repository}/pulls", params={"state": state, "per_page": limit}
        )

    def get_pull_request(self, repository: str, number: int) -> JsonObject:
        return self._request("GET", f"/repos/{repository}/pulls/{number}")

    def list_issues(self, repository: str, state: str, limit: int) -> list[JsonObject]:
        values = self._request(
            "GET", f"/repos/{repository}/issues", params={"state": state, "per_page": limit}
        )
        return [item for item in values if "pull_request" not in item]

    def get_issue(self, repository: str, number: int) -> JsonObject:
        value = self._request("GET", f"/repos/{repository}/issues/{number}")
        if "pull_request" in value:
            raise GitHubValidationError("Requested number belongs to a pull request")
        return value

    def create_issue(
        self, repository: str, title: str, body: str, idempotency_key: str | None
    ) -> JsonObject:
        marker = _marker("issue", idempotency_key)
        if marker:
            for issue in self.list_issues(repository, "all", 100):
                if marker in (issue.get("body") or ""):
                    return issue | {"_already_existed": True}
            body = _append_marker(body, marker)
        return self._request(
            "POST", f"/repos/{repository}/issues", json={"title": title, "body": body}
        )

    def comment_issue(
        self, repository: str, number: int, body: str, idempotency_key: str | None
    ) -> JsonObject:
        marker = _marker("comment", idempotency_key)
        if marker:
            comments = self._request(
                "GET", f"/repos/{repository}/issues/{number}/comments", params={"per_page": 100}
            )
            for comment in comments:
                if marker in (comment.get("body") or ""):
                    return comment | {"_already_existed": True}
            body = _append_marker(body, marker)
        return self._request(
            "POST", f"/repos/{repository}/issues/{number}/comments", json={"body": body}
        )

    def create_branch(self, repository: str, branch: str, from_ref: str) -> JsonObject:
        source = self._request(
            "GET", f"/repos/{repository}/git/ref/heads/{quote(from_ref, safe='')}"
        )
        source_sha = source["object"]["sha"]
        try:
            existing = self._request(
                "GET", f"/repos/{repository}/git/ref/heads/{quote(branch, safe='')}"
            )
        except GitHubNotFoundError:
            existing = None
        if existing:
            if existing["object"]["sha"] != source_sha:
                raise GitHubValidationError("Branch already exists at a different commit")
            return existing | {"_already_existed": True}
        return self._request(
            "POST",
            f"/repos/{repository}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": source_sha},
        )

    def create_or_update_file(
        self,
        repository: str,
        path: str,
        branch: str,
        content: str,
        message: str,
        expected_sha: str | None,
    ) -> JsonObject:
        safe_path = quote(path, safe="/")
        try:
            current = self.read_file(repository, path, branch)
        except GitHubNotFoundError:
            current = None
        if current is not None and current.get("type") != "file":
            raise GitHubValidationError("GitHub path is not a file")
        current_sha = current.get("sha") if current else None
        if expected_sha is not None and expected_sha != current_sha:
            raise GitHubValidationError("File changed since the expected SHA")
        payload: JsonObject = {
            "message": message,
            "branch": branch,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }
        if current_sha:
            payload["sha"] = current_sha
        result = self._request("PUT", f"/repos/{repository}/contents/{safe_path}", json=payload)
        return result | {"_created": current_sha is None}

    def open_pull_request(
        self, repository: str, head: str, base: str, title: str, body: str
    ) -> JsonObject:
        owner = repository.split("/", 1)[0]
        existing = self._request(
            "GET",
            f"/repos/{repository}/pulls",
            params={"state": "open", "head": f"{owner}:{head}", "base": base, "per_page": 10},
        )
        if existing:
            return existing[0] | {"_already_existed": True}
        return self._request(
            "POST",
            f"/repos/{repository}/pulls",
            json={"head": head, "base": base, "title": title, "body": body},
        )


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _marker(kind: str, key: str | None) -> str | None:
    return f"<!-- kiko-{kind}-idempotency:{key} -->" if key else None


def _append_marker(body: str, marker: str) -> str:
    return f"{body.rstrip()}\n\n{marker}".strip()


GitHubClientFactory = Callable[[str, float], GitHubClient]


def build_github_client(token: str, timeout_seconds: float) -> GitHubClient:
    return HttpGitHubClient(GitHubClientConfig(token=token, timeout_seconds=timeout_seconds))
