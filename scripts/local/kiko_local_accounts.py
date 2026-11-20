"""Create temporary acceptance-test accounts in the Kiko local test environment.

One fictitious owner (accept-owner-<stamp>@example.com) registers, verifies through
Mailpit and completes onboarding; it then invites one account for every invitable role
(admin, manager, member, viewer), which register, verify and accept. The workspace is
moved to the Business plan in the local database (the trial allows 3 seats and there is
no billing API yet), and a separate platform administrator (is_superuser) is created for
the platform admin screens. Passwords are random. The credentials are written to <state>/test-accounts.txt (mode 600) and never
printed. Invoked by `scripts/local/kiko-local.sh accounts`. Local only.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kiko_local_smoke import Api, mail_link, psql, token_of

ROLES = ("admin", "manager", "member", "viewer")
ORIGIN_SAFE = ("127.0.0.1", "localhost")


def fail(message: str) -> None:
    print(f"FAIL  {message}", flush=True)
    raise SystemExit(1)


def register_and_verify(api: Api, mailpit: str, email: str, name: str) -> str:
    password = f"Accept-{secrets.token_urlsafe(9)}1a"
    started = time.time()
    status, _ = api.call(
        "POST",
        "/auth/register",
        {
            "email": email,
            "password": password,
            "full_name": name,
            "terms_accepted": True,
            "privacy_accepted": True,
        },
    )
    if status != 202:
        fail(f"register {email}: HTTP {status}")
    link = mail_link(mailpit, email, "verify", started)
    if not link:
        fail(f"no verification email for {email}")
    status, _ = api.call("POST", "/auth/verify-email", {"token": token_of(link)})
    if status != 200:
        fail(f"verify {email}: HTTP {status}")
    return password


def login(api: Api, email: str, password: str) -> str:
    for _ in range(4):
        status, body = api.call(
            "POST", "/auth/login", {"email": email, "password": password}
        )
        if status == 429:  # auth rate limit (10/min/IP)
            time.sleep(20)
            continue
        if status != 200:
            fail(f"login {email}: HTTP {status}")
        return body["access_token"]
    fail(f"login {email}: rate limited")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--mailpit", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--pg-bin", required=True)
    args = parser.parse_args()
    for url in (args.api, args.mailpit):
        if not any(host in url for host in ORIGIN_SAFE):
            fail(f"refusing to run against non-local URL {url}")

    stamp = int(time.time())
    owner_email = f"accept-owner-{stamp}@example.com"
    owner_api = Api(args.api)
    owner_password = register_and_verify(
        owner_api, args.mailpit, owner_email, "Acceptance Owner"
    )
    owner_token = login(owner_api, owner_email, owner_password)
    status, body = owner_api.call("GET", "/workspaces/onboarding", token=owner_token)
    workspace_id = (body or {}).get("workspace_id")
    if status != 200 or not workspace_id:
        fail(f"owner workspace: HTTP {status}")
    status, _ = owner_api.call(
        "PATCH",
        "/workspaces/onboarding",
        {
            "step": 8,
            "company_name": "Pixart Acceptance",
            "company_description": "Fictitious company for local acceptance testing.",
            "primary_objectives": ["Grow sales", "Automate operations"],
            "complete": True,
        },
        token=owner_token,
    )
    if status != 200:
        fail(f"owner onboarding: HTTP {status}")
    print(f"PASS  owner created and onboarded (workspace {workspace_id})", flush=True)
    psql(
        args.pg_bin,
        "update workspace_subscriptions set plan_code = 'business', status = 'active', "
        f"trial_ends_at = null where workspace_id = '{workspace_id}'",
    )
    status, body = owner_api.call("GET", "/commercial/subscription", token=owner_token)
    if status != 200 or ((body or {}).get("plan") or {}).get("code") != "business":
        fail(f"workspace not on the business plan: HTTP {status} {body}")
    print("PASS  workspace moved to the Business plan (local database)", flush=True)

    accounts = [("owner", owner_email, owner_password)]
    for role in ROLES:
        email = f"accept-{role}-{stamp}@example.com"
        started = time.time()
        status, _ = owner_api.call(
            "POST",
            f"/workspaces/{workspace_id}/invitations",
            {"email": email, "role": role},
            token=owner_token,
        )
        if status != 201:
            fail(f"invite {role}: HTTP {status}")
        invite_link = mail_link(args.mailpit, email, "join", started)
        if not invite_link:
            fail(f"no invitation email for {role}")
        api = Api(args.api)
        password = register_and_verify(
            api, args.mailpit, email, f"Acceptance {role.title()}"
        )
        token = login(api, email, password)
        status, body = api.call(
            "POST",
            "/workspaces/invitations/accept",
            {"token": token_of(invite_link)},
            token=token,
        )
        if status != 200 or (body or {}).get("role") != role:
            fail(f"accept invitation as {role}: HTTP {status} {body}")
        accounts.append((role, email, password))
        print(f"PASS  {role} invited, verified and joined", flush=True)

    platform_email = f"accept-platform-{stamp}@example.com"
    platform_api = Api(args.api)
    platform_password = register_and_verify(
        platform_api, args.mailpit, platform_email, "Acceptance Platform Admin"
    )
    psql(
        args.pg_bin,
        f"update users set is_superuser = true where email = '{platform_email}'",
    )
    platform_token = login(platform_api, platform_email, platform_password)
    status, _ = platform_api.call(
        "GET", "/platform-admin/overview", token=platform_token
    )
    if status != 200:
        fail(f"platform admin overview: HTTP {status}")
    accounts.append(("platform", platform_email, platform_password))
    print("PASS  platform administrator created", flush=True)

    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    target = state / "test-accounts.txt"
    lines = [
        "# Kiko local acceptance accounts (fictitious, local only).",
        f"# Created {time.strftime('%Y-%m-%d %H:%M')} - workspace 'Pixart Acceptance' {workspace_id}",
        "# role      email                                   password",
    ]
    lines += [
        f"{role:<10} {email:<40} {password}" for role, email, password in accounts
    ]
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"PASS  {len(accounts)} accounts written to {target}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
