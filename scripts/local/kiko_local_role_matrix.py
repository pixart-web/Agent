"""Role permission sweep inside one workspace, against the local Kiko API.

Uses the accounts created by `kiko-local.sh accounts`. The owner creates one resource of
each kind in the shared workspace; then each probed role calls every mutating API
operation (POST/PUT/PATCH/DELETE) with the owner's identifiers and a schema-valid body.

Expected policy:
  viewer  read-only: every workspace write must be refused.
  member, manager  no workspace administration: members, invitations, workspace
                   settings, subscription and platform admin must be refused.
Self-service operations on the caller's own account (auth, notifications, workspace
switching, accepting invitations) are excluded.

Invoked by `scripts/local/kiko-local.sh role-matrix`. Local hosts only; fictitious data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiko_local_idor_sweep as idor
import kiko_local_smoke as smoke

PARAM = re.compile(r"{(\w+)}")
SELF_SERVICE = (
    "/api/v1/auth/",
    "/api/v1/notifications",
    "/api/v1/workspaces/switch",
    "/api/v1/workspaces/invitations/accept",
    "/api/v1/workspaces/onboarding",  # per-user progress; company fields are admin-only
)
READS = ("/api/v1/knowledge/workspaces/{workspace_id}/search",)  # POST that only reads
ADMIN_ONLY = (
    "/api/v1/workspaces/{workspace_id}/invitations",
    "/api/v1/workspaces/{workspace_id}/members",
    "/api/v1/workspaces/{workspace_id}/transfer-ownership",
    "/api/v1/workspaces/settings",
    "/api/v1/commercial/",
    "/api/v1/platform-admin/",
)
METHOD_ORDER = {"post": 0, "put": 1, "patch": 2, "delete": 3}


def load_accounts(path: Path) -> dict[str, tuple[str, str]]:
    accounts = {}
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        role, email, password = line.split()
        accounts[role] = (email, password)
    return accounts


def login(api: smoke.Api, email: str, password: str) -> str:
    for _ in range(6):
        status, body = api.call(
            "POST", "/auth/login", {"email": email, "password": password}
        )
        if status == 429:
            time.sleep(15)
            continue
        if status != 200:
            raise SystemExit(f"login {email}: HTTP {status}")
        return body["access_token"]
    raise SystemExit(f"login {email}: rate limited")


def operations(spec: dict, admin_only: bool) -> list[tuple[str, str, dict]]:
    found = []
    for path, ops in spec["paths"].items():
        if (
            not path.startswith("/api/v1/")
            or path.startswith(SELF_SERVICE)
            or path in READS
        ):
            continue
        if admin_only and not path.startswith(ADMIN_ONLY):
            continue
        for method, operation in ops.items():
            if method in METHOD_ORDER:
                found.append((path, method, operation))
    return sorted(found, key=lambda item: (METHOD_ORDER[item[1]], item[0]))


def sweep(
    role: str,
    api: smoke.Api,
    token: str,
    ids: dict[str, str],
    spec: dict,
    schema: idor.Schema,
    admin_only: bool,
) -> tuple[int, list[str], list[str]]:
    allowed: list[str] = []
    skipped: list[str] = []
    codes: dict[int, int] = {}
    probed = 0
    for path, method, operation in operations(spec, admin_only):
        missing = [p for p in PARAM.findall(path) if p not in ids]
        if missing:
            skipped.append(f"{method.upper()} {path} (no {', '.join(missing)})")
            continue
        concrete = path
        for p in PARAM.findall(path):
            concrete = concrete.replace("{" + p + "}", ids[p])
        body = schema.body(operation) if method in {"post", "put", "patch"} else None
        status, reply = api.call(
            method.upper(), concrete.removeprefix("/api/v1"), body, token=token
        )
        probed += 1
        codes[status] = codes.get(status, 0) + 1
        if 200 <= status < 300:
            allowed.append(
                f"{method.upper()} {path} -> HTTP {status} {str(reply)[:120]}"
            )
    print(f"  {role}: refusal codes {dict(sorted(codes.items()))}", flush=True)
    return probed, allowed, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--accounts", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()
    spec = json.load(urllib.request.urlopen(f"{args.api}/openapi.json", timeout=30))
    schema = idor.Schema(spec)
    accounts = load_accounts(args.accounts)

    owner_api = smoke.Api(args.api)
    owner_token = login(owner_api, *accounts["owner"])
    report: dict[str, dict] = {}
    failures = 0
    for role, admin_only in (("viewer", False), ("member", True), ("manager", True)):
        # Fresh owner resources for every role: a role that wrongly deletes something must
        # not hide defects from the next one.
        ids = idor.create_resources(owner_api, owner_token)
        idor.discover_more(owner_api, owner_token, ids, spec, schema)
        api = smoke.Api(args.api)
        token = login(api, *accounts[role])
        # Accepting an invitation keeps the personal workspace active; act in the shared one.
        status, _ = api.call(
            "POST",
            "/workspaces/switch",
            {"workspace_id": ids["workspace_id"]},
            token=token,
        )
        if status != 204:
            raise SystemExit(
                f"{role}: could not switch to the shared workspace (HTTP {status})"
            )
        _, onboarding = api.call("GET", "/workspaces/onboarding", token=token)
        if (onboarding or {}).get("workspace_id") != ids["workspace_id"]:
            raise SystemExit(f"{role}: active workspace did not change")
        _, members = owner_api.call(
            "GET",
            f"/knowledge/workspaces/{ids['workspace_id']}/members",
            token=owner_token,
        )
        for member in (members or {}).get("members", []):
            if member.get("role") == "admin":
                ids["member_id"] = str(member.get("id") or member.get("user_id"))
        probed, allowed, skipped = sweep(
            role, api, token, ids, spec, schema, admin_only
        )
        scope = "workspace administration" if admin_only else "every workspace write"
        ok = smoke.check(
            f"{role}: refused {scope}",
            not allowed,
            f"{probed} operations probed, {len(allowed)} allowed",
        )
        failures += 0 if ok else 1
        for item in allowed:
            print(f"  ALLOWED {item}")
        report[role] = {"probed": probed, "allowed": allowed, "not_covered": skipped}
    args.state.mkdir(parents=True, exist_ok=True)
    (args.state / "role-matrix.json").write_text(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
