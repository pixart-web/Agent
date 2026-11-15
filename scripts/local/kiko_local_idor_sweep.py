"""Cross-tenant authorization sweep (IDOR) against the local Kiko API.

Company A creates one resource of each kind through the real API. Company B (another
workspace, another user) then calls every API operation that takes a resource identifier,
substituting A's identifiers, with a schema-valid body. Any 2xx answer is a cross-tenant
access defect. Operations whose identifier could not be produced are listed as not covered.

Invoked by `scripts/local/kiko-local.sh idor-sweep`. Local hosts only; fictitious data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiko_local_ai_eval as ai
import kiko_local_smoke as smoke

PARAM = re.compile(r"{(\w+)}")


class Schema:
    def __init__(self, spec: dict) -> None:
        self.spec = spec

    def resolve(self, node: dict) -> dict:
        while "$ref" in node:
            name = node["$ref"].split("/")[-1]
            node = self.spec["components"]["schemas"][name]
        return node

    def sample(self, node: dict, depth: int = 0) -> object:
        node = self.resolve(node)
        if depth > 6:
            return None
        for key in ("anyOf", "oneOf"):
            if key in node:
                options = [
                    o for o in node[key] if self.resolve(o).get("type") != "null"
                ]
                return self.sample(options[0], depth + 1) if options else None
        if "allOf" in node:
            return self.sample(node["allOf"][0], depth + 1)
        if "default" in node:
            return node["default"]
        if "enum" in node:
            return node["enum"][0]
        if "const" in node:
            return node["const"]
        kind = node.get("type")
        if kind == "object" or "properties" in node:
            required = node.get("required", [])
            props = node.get("properties", {})
            return {k: self.sample(props[k], depth + 1) for k in required if k in props}
        if kind == "array":
            count = node.get("minItems", 0)
            return [self.sample(node.get("items", {}), depth + 1) for _ in range(count)]
        if kind == "integer":
            return max(node.get("minimum", 1), 1)
        if kind == "number":
            return max(node.get("minimum", 1), 1)
        if kind == "boolean":
            return False
        fmt = node.get("format", "")
        if fmt == "email":
            return "idor-probe@example.com"
        if fmt in {"uri", "url"}:
            return "https://example.com"
        if fmt == "uuid":
            return "00000000-0000-4000-8000-000000000000"
        if fmt == "date-time":
            return "2030-01-01T10:00:00Z"
        if fmt == "date":
            return "2030-01-01"
        text = "IDOR probe value"
        minimum, maximum = node.get("minLength", 0), node.get("maxLength", 200)
        text = (text * (minimum // len(text) + 1))[
            : max(minimum, min(len(text), maximum))
        ]
        return text

    def body(self, operation: dict) -> dict | None:
        content = (operation.get("requestBody") or {}).get("content", {})
        schema = (content.get("application/json") or {}).get("schema")
        return self.sample(schema) if schema else None


def create_resources(api: smoke.Api, token: str) -> dict[str, str]:
    """Create one resource of each kind for company A; returns path-parameter values."""
    ids: dict[str, str] = {}

    def keep(name: str, status: int, body: object, key: str = "id") -> dict:
        if status in {200, 201} and isinstance(body, dict) and body.get(key):
            ids[name] = str(body[key])
        return body if isinstance(body, dict) else {}

    _, onboarding = api.call("GET", "/workspaces/onboarding", token=token)
    ids["workspace_id"] = onboarding["workspace_id"]
    _, me = api.call("GET", "/auth/me", token=token)
    ids["user_id"] = me["id"]
    _, sessions = api.call("GET", "/auth/sessions", token=token)
    if sessions:
        ids["session_id"] = sessions[0]["id"]

    status, conv = api.call(
        "POST",
        "/conversations",
        {"message": "Preparar relatório interno."},
        token=token,
    )
    keep("conversation_id", status, (conv or {}).get("conversation"))
    command = keep("command_id", status, (conv or {}).get("command"))
    status, plan = api.call(
        "POST",
        f"/commands/{command.get('id')}/plan",
        {
            "title": "Plano manual",
            "objective": "Relatório interno",
            "summary": "Plano de teste",
        },
        token=token,
    )
    plan = keep("plan_id", status, plan)
    status, task = api.call(
        "POST",
        f"/plans/{plan.get('id')}/tasks",
        {
            "agent_id": "marketing",
            "title": "Rascunho",
            "instructions": "Preparar rascunho interno",
            "priority": "normal",
            "risk_level": "green",
            "sequence": 1,
        },
        token=token,
    )
    task = keep("task_id", status, task)
    status, task2 = api.call(
        "POST",
        f"/plans/{plan.get('id')}/tasks",
        {
            "agent_id": "marketing",
            "title": "Revisão",
            "instructions": "Rever rascunho",
            "priority": "normal",
            "risk_level": "green",
            "sequence": 2,
        },
        token=token,
    )
    status, dep = api.call(
        "POST",
        f"/tasks/{(task2 or {}).get('id')}/dependencies",
        {"depends_on_task_id": task.get("id")},
        token=token,
    )
    keep("dependency_id", status, dep)
    api.call("POST", f"/plans/{plan.get('id')}/approve", {}, token=token)
    api.call(
        "POST", f"/tasks/{task.get('id')}/transition", {"status": "ready"}, token=token
    )
    status, action = api.call(
        "POST",
        f"/tasks/{task.get('id')}/actions",
        {
            "tool_name": "internal.simulate_external_action",
            "input_payload": {
                "action": "notify_client",
                "description": "Notify the fictitious client",
            },
        },
        token=token,
    )
    action = keep("action_id", status, action)
    if "action_id" not in ids:
        print(f"  could not create action_id: HTTP {status} {str(action)[:200]}")
    api.call("POST", f"/actions/{action.get('id')}/dispatch", {}, token=token)
    _, approvals = api.call("GET", "/approvals", token=token)
    items = (
        approvals if isinstance(approvals, list) else (approvals or {}).get("items", [])
    )
    if items:
        ids["approval_id"] = str(items[0]["id"])
    status, execs = api.call(
        "GET", f"/actions/{action.get('id')}/executions", token=token
    )
    items = execs if isinstance(execs, list) else (execs or {}).get("items", [])
    if items:
        ids["execution_id"] = str(items[0]["id"])

    status, project = api.call(
        "POST",
        "/projects",
        {"name": "Projeto IDOR", "description": "Teste"},
        token=token,
    )
    project = keep("project_id", status, project)
    status, milestone = api.call(
        "POST",
        f"/projects/{project.get('id')}/milestones",
        {"title": "Marco 1"},
        token=token,
    )
    keep("milestone_id", status, milestone)
    return ids


def discover_more(
    api: smoke.Api, token: str, ids: dict[str, str], spec: dict, schema: Schema
) -> None:
    """Create remaining kinds generically: POST collection endpoints with schema-valid bodies."""
    creators = {
        "automation_id": "/api/v1/automations",
        "client_id": "/api/v1/crm/clients",
        "campaign_id": "/api/v1/marketing/campaigns",
        "content_id": "/api/v1/marketing/content",
        "organization_id": "/api/v1/crm/organizations",
        "contact_id": "/api/v1/crm/contacts",
        "opportunity_id": "/api/v1/crm/opportunities",
    }
    links = {  # creation order matters: these kinds belong to a previously created parent
        "client_id": {"organization_id": "organization_id"},
        "content_id": {"campaign_id": "campaign_id"},
        "opportunity_id": {"client_id": "client_id"},
    }
    extra = {"automation_id": {"trigger_type": "manual"}}
    if "/api/v1/crm/pipelines" in spec["paths"]:
        body = schema.body(spec["paths"]["/api/v1/crm/pipelines"]["post"]) or {}
        status, pipeline = api.call("POST", "/crm/pipelines", body, token=token)
        if status in {200, 201} and isinstance(pipeline, dict):
            ids["pipeline_id"] = str(pipeline["id"])
            stages = pipeline.get("stages") or []
            if stages:
                ids["stage_id"] = str(stages[0]["id"])
        links["opportunity_id"].update(
            {"pipeline_id": "pipeline_id", "stage_id": "stage_id"}
        )
    order = [
        "automation_id",
        "organization_id",
        "contact_id",
        "client_id",
        "opportunity_id",
        "campaign_id",
        "content_id",
    ]
    for name in order:
        path = creators[name]
        if (
            name in ids
            or path not in spec["paths"]
            or "post" not in spec["paths"][path]
        ):
            continue
        body = schema.body(spec["paths"][path]["post"]) or {}
        body.update(extra.get(name, {}))
        body.update(
            {
                field: ids[source]
                for field, source in links.get(name, {}).items()
                if source in ids
            }
        )
        status, created = api.call(
            "POST", path.removeprefix("/api/v1"), body, token=token
        )
        if status in {200, 201} and isinstance(created, dict) and created.get("id"):
            ids[name] = str(created["id"])
        else:
            print(f"  could not create {name}: HTTP {status} {str(created)[:160]}")
    knowledge = "/api/v1/knowledge/workspaces/{workspace_id}/items"
    if knowledge in spec["paths"] and "post" in spec["paths"][knowledge]:
        body = schema.body(spec["paths"][knowledge]["post"]) or {}
        status, item = api.call(
            "POST",
            f"/knowledge/workspaces/{ids['workspace_id']}/items",
            body,
            token=token,
        )
        if status in {200, 201} and isinstance(item, dict) and item.get("id"):
            ids["item_id"] = str(item["id"])
        else:
            print(f"  could not create item_id: HTTP {status} {str(item)[:160]}")
    status, invitation = api.call(
        "POST",
        f"/workspaces/{ids['workspace_id']}/invitations",
        {"email": "idor-invitee@example.com", "role": "member"},
        token=token,
    )
    if status == 201 and isinstance(invitation, dict):
        ids["invitation_id"] = str(invitation["id"])
    status, members = api.call(
        "GET", f"/knowledge/workspaces/{ids['workspace_id']}/members", token=token
    )
    items = (members or {}).get("members", []) if isinstance(members, dict) else []
    if status == 200 and items:
        ids["member_id"] = str(items[0].get("id") or items[0].get("user_id"))
    _, notes = api.call("GET", "/notifications", token=token)
    items = (notes or {}).get("notifications", []) if isinstance(notes, dict) else []
    if items:
        ids["notification_id"] = str(items[0]["id"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--mailpit", required=True)
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()
    spec = json.load(urllib.request.urlopen(f"{args.api}/openapi.json", timeout=30))
    schema = Schema(spec)
    api_a, api_b = smoke.Api(args.api), smoke.Api(args.api)
    token_a, _ = ai.account(api_a, args.mailpit, "idor-a")
    token_b, _ = ai.account(api_b, args.mailpit, "idor-b")
    ids = create_resources(api_a, token_a)
    discover_more(api_a, token_a, ids, spec, schema)
    print(f"company A resources: {sorted(ids)}")

    leaks: list[str] = []
    covered = uncovered = 0
    not_covered: list[str] = []
    for path, operations in sorted(spec["paths"].items()):
        params = PARAM.findall(path)
        if not params or not path.startswith("/api/v1/"):
            continue
        for method, operation in operations.items():
            missing = [p for p in params if p not in ids]
            if missing:
                uncovered += 1
                not_covered.append(f"{method.upper()} {path} (no {', '.join(missing)})")
                continue
            concrete = path
            for p in params:
                concrete = concrete.replace("{" + p + "}", ids[p])
            body = (
                schema.body(operation) if method in {"post", "put", "patch"} else None
            )
            status, reply = api_b.call(
                method.upper(), concrete.removeprefix("/api/v1"), body, token=token_b
            )
            covered += 1
            if 200 <= status < 300:
                leaks.append(
                    f"{method.upper()} {path} -> HTTP {status} {str(reply)[:160]}"
                )
    smoke.check(
        "IDOR sweep: no cross-tenant 2xx",
        not leaks,
        f"{covered} operations probed, {len(leaks)} leaks",
    )
    for leak in leaks:
        print(f"  LEAK {leak}")
    print(f"\nnot covered ({uncovered}):")
    for item in not_covered:
        print(f"  {item}")
    args.state.mkdir(parents=True, exist_ok=True)
    (args.state / "idor-sweep.json").write_text(
        json.dumps(
            {
                "covered": covered,
                "leaks": leaks,
                "not_covered": not_covered,
                "ids": sorted(ids),
            },
            indent=2,
        )
    )
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
