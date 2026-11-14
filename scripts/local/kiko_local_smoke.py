"""Backend smoke test for the Kiko local test environment.

Runs real HTTP requests against the local API with a fictitious account
(local-smoke-<timestamp>@example.com), reads the emails captured by Mailpit, and checks
PostgreSQL, Redis and Celery directly. Invoked by `scripts/local/kiko-local.sh test`,
which loads the API environment first. Standard library only (plus the API venv for the
Celery check). It refuses to run against anything that is not on this machine.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

COOKIE = "agent_refresh_token"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(
        f"{'PASS' if ok else 'FAIL'}  {name}{f'  ({detail})' if detail else ''}",
        flush=True,
    )
    return ok


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.refresh: str | None = None

    def call(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        token: str | None = None,
        send_cookie: bool = False,
    ) -> tuple[int, dict | None]:
        data = json.dumps(body).encode() if body is not None else None
        if path not in ("/health", "/ready"):
            path = "/api/v1" + path
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("User-Agent", "kiko-local-smoke/1")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        if send_cookie and self.refresh:
            request.add_header("Cookie", f"{COOKIE}={self.refresh}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, raw, headers = (
                    response.status,
                    response.read(),
                    response.headers,
                )
        except urllib.error.HTTPError as error:
            status, raw, headers = error.code, error.read(), error.headers
        for header in headers.get_all("Set-Cookie") or []:
            match = re.match(rf"{COOKIE}=([^;]*)", header)
            if match:
                self.refresh = match.group(1) or None
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = None
        return status, payload


def mail_link(mailpit: str, email: str, subject_word: str, after: float) -> str | None:
    """Wait for the newest email to `email` whose subject contains `subject_word`."""
    query = urllib.parse.urlencode({"query": f'to:"{email}"'})
    deadline = time.time() + 45
    while time.time() < deadline:
        with urllib.request.urlopen(
            f"{mailpit}/api/v1/search?{query}", timeout=10
        ) as r:
            messages = json.load(r).get("messages") or []
        for message in messages:
            created = message.get("Created", "")
            if subject_word.lower() not in message.get("Subject", "").lower():
                continue
            with urllib.request.urlopen(
                f"{mailpit}/api/v1/message/{message['ID']}", timeout=10
            ) as r:
                text = json.load(r).get("Text", "")
            match = re.search(r"https?://\S+\?token=[A-Za-z0-9_.~-]+", text)
            if match and created and _iso_ts(created) >= after - 2:
                return match.group(0)
        time.sleep(1)
    return None


def _iso_ts(value: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(value).timestamp()


def token_of(link: str) -> str:
    return urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)["token"][0]


def psql(pg_bin: str, sql: str) -> str:
    url = urllib.parse.urlsplit(os.environ["DATABASE_URL"].replace("+psycopg", ""))
    env = {**os.environ, "PGPASSWORD": urllib.parse.unquote(url.password or "")}
    out = subprocess.run(
        [
            f"{pg_bin}/psql",
            "-h",
            url.hostname,
            "-p",
            str(url.port),
            "-U",
            url.username,
            "-d",
            url.path.lstrip("/"),
            "-tAc",
            sql,
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return out.stdout.strip()


def run_full(api: Api, mailpit: str, state: Path, pg_bin: str) -> None:
    stamp = int(time.time())
    email = f"local-smoke-{stamp}@example.com"
    password = f"Smoke-{secrets.token_hex(5)}1a"
    started = time.time()

    status, body = api.call("GET", "/health")
    check(
        "API health",
        status == 200 and body and body.get("status") == "healthy",
        str(body),
    )
    status, body = api.call("GET", "/ready")
    check("API readiness (database + redis)", status == 200, json.dumps(body))

    status, _ = api.call(
        "POST",
        "/auth/register",
        {
            "email": email,
            "password": password,
            "full_name": "Local Smoke Tester",
            "terms_accepted": True,
            "privacy_accepted": True,
        },
    )
    check("register fictitious user", status == 202, email)

    status, _ = api.call("POST", "/auth/login", {"email": email, "password": password})
    check("login refused before email verification", status == 403, f"HTTP {status}")

    link = mail_link(mailpit, email, "verify", started)
    check(
        "verification email captured by Mailpit", link is not None, link or "no email"
    )
    if not link:
        return
    status, _ = api.call("POST", "/auth/verify-email", {"token": token_of(link)})
    check("verify email with emailed token", status == 200, f"HTTP {status}")

    status, body = api.call(
        "POST", "/auth/login", {"email": email, "password": password}
    )
    access = (body or {}).get("access_token")
    check(
        "login after verification",
        status == 200 and bool(access) and bool(api.refresh),
        f"HTTP {status}, refresh cookie {'set' if api.refresh else 'missing'}",
    )
    status, body = api.call("GET", "/auth/me", token=access)
    check(
        "authenticated /auth/me", status == 200 and (body or {}).get("email") == email
    )

    old_refresh = api.refresh
    status, body = api.call("POST", "/auth/refresh", send_cookie=True)
    access = (body or {}).get("access_token") or access
    check(
        "session refresh rotates the refresh token",
        status == 200 and api.refresh is not None and api.refresh != old_refresh,
        f"HTTP {status}",
    )

    status, body = api.call("GET", "/workspaces/onboarding", token=access)
    check(
        "workspace exists for new account",
        status == 200 and bool((body or {}).get("workspace_id")),
    )
    workspace_id = (body or {}).get("workspace_id")
    status, body = api.call(
        "PATCH",
        "/workspaces/onboarding",
        {
            "step": 8,
            "company_name": "Local Smoke Lda",
            "company_description": "Fictitious company.",
            "primary_objectives": ["Test the local environment"],
            "complete": True,
        },
        token=access,
    )
    check(
        "onboarding completes workspace setup",
        status == 200
        and (body or {}).get("completed_at") is not None
        and (body or {}).get("company_name") == "Local Smoke Lda",
        f"HTTP {status}",
    )

    reset_started = time.time()
    status, _ = api.call("POST", "/auth/password-reset/request", {"email": email})
    link = mail_link(mailpit, email, "reset", reset_started)
    check(
        "password reset email captured by Mailpit", status == 200 and link is not None
    )
    new_password = f"Smoke-{secrets.token_hex(5)}2b"
    if link:
        status, _ = api.call(
            "POST",
            "/auth/password-reset/confirm",
            {"token": token_of(link), "password": new_password},
        )
        check("password reset confirm", status == 200, f"HTTP {status}")
        status, _ = api.call(
            "POST", "/auth/login", {"email": email, "password": password}
        )
        check("old password rejected after reset", status == 401, f"HTTP {status}")
        status, body = api.call(
            "POST", "/auth/login", {"email": email, "password": new_password}
        )
        check("login with new password", status == 200, f"HTTP {status}")
        access = (body or {}).get("access_token")
        password = new_password

    logged_out = api.refresh
    status, _ = api.call("POST", "/auth/logout", send_cookie=True)
    check("logout", status == 204, f"HTTP {status}")
    api.refresh = logged_out  # replay the token that was just logged out
    status, _ = api.call("POST", "/auth/refresh", send_cookie=True)
    check("refresh refused after logout", status == 401, f"HTTP {status}")

    users = psql(
        pg_bin,
        f"select count(*) from users where email = '{email}' and email_verified_at is not null",
    )
    members = psql(
        pg_bin,
        f"select count(*) from workspace_members where workspace_id = '{workspace_id}'",
    )
    check(
        "PostgreSQL persisted user and workspace membership",
        users == "1" and members == "1",
        f"users={users} members={members}",
    )

    redis_ok = _redis_roundtrip()
    check("Redis read/write", redis_ok)
    check_celery()

    state.mkdir(parents=True, exist_ok=True)
    account = state / "last-account.json"
    account.write_text(
        json.dumps({"email": email, "password": password, "workspace_id": workspace_id})
    )
    account.chmod(0o600)
    print(f"\nfictitious account saved for `test-persisted`: {email}")


def _redis_roundtrip() -> bool:
    import redis  # API venv dependency

    client = redis.Redis.from_url(os.environ["REDIS_URL"])
    key = f"kiko-local:smoke:{secrets.token_hex(4)}"
    client.set(key, "ok", ex=60)
    return client.get(key) == b"ok"


def check_celery() -> None:
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "app.execution.celery_app:celery_app",
            "inspect",
            "registered",
            "--timeout",
            "5",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        replies = (
            json.loads(out.stdout.strip().splitlines()[-1])
            if out.stdout.strip()
            else {}
        )
    except ValueError:
        replies = {}
    tasks = (
        [task for reply in replies.values() for task in reply]
        if isinstance(replies, dict)
        else []
    )
    check(
        "Celery worker online with execution tasks registered",
        any("execute_task_execution" in task for task in tasks),
        f"{len(replies)} worker(s)"
        if replies
        else (out.stderr.strip()[-200:] or "no reply"),
    )


def run_persisted(api: Api, state: Path) -> None:
    account = json.loads((state / "last-account.json").read_text())
    status, body = api.call("GET", "/health")
    check("API health after restart", status == 200)
    status, body = api.call(
        "POST",
        "/auth/login",
        {"email": account["email"], "password": account["password"]},
    )
    access = (body or {}).get("access_token")
    check(
        "account from before the restart can sign in", status == 200, account["email"]
    )
    status, body = api.call("GET", "/workspaces/onboarding", token=access)
    check(
        "workspace survived the restart",
        status == 200
        and (body or {}).get("workspace_id") == account["workspace_id"]
        and (body or {}).get("completed_at") is not None,
    )
    api.call("POST", "/auth/logout", send_cookie=True)
    check("Redis read/write after restart", _redis_roundtrip())
    check_celery()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--mailpit", required=True)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--pg-bin", required=True)
    parser.add_argument("--persisted", action="store_true")
    args = parser.parse_args()
    for url in (args.api, args.mailpit):
        host = urllib.parse.urlsplit(url).hostname
        if host not in {"127.0.0.1", "localhost"}:
            print(f"refusing to run against non-local host {host}", file=sys.stderr)
            return 2
    api = Api(args.api)
    try:
        if args.persisted:
            run_persisted(api, args.state)
        else:
            run_full(api, args.mailpit, args.state, args.pg_bin)
    except Exception as error:  # noqa: BLE001 - report, never hide
        check("smoke test aborted", False, f"{type(error).__name__}: {error}")
    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
