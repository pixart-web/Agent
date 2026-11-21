"""End-to-end workflow checks against the running local stack (backlog B5).

1. Projects and tasks: a project links the tasks of an approved plan, reports them and its
   progress follows task completion.
2. Scheduled automations: a due schedule is picked up by the running automation scheduler
   (no manual trigger), creates exactly one command and advances its next run.

Uses the owner account from `kiko-local.sh accounts`. Creates fictitious records only and
pauses the automation it creates.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

FAILURES: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}{f'  ({detail})' if detail else ''}")
    if not ok:
        FAILURES.append(label)


class Api:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/") + "/api/v1"
        self.token = ""

    def call(
        self, method: str, path: str, body: object | None = None
    ) -> tuple[int, object]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.base + path,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, json.loads(raw) if raw else None


def owner_credentials(path: Path) -> tuple[str, str]:
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts and parts[0] == "owner":
            return parts[1], parts[2]
    raise SystemExit(f"no owner account in {path}")


def projects_and_tasks(api: Api, stamp: str) -> None:
    status, project = api.call("POST", "/projects", {"name": f"Workflow check {stamp}"})
    check(status == 201, "create a project", str(status))
    _, command = api.call("POST", "/commands", {"input": f"Workflow check {stamp}"})
    _, plan = api.call(
        "POST",
        f"/commands/{command['id']}/plan",
        {"title": "Workflow check", "objective": "Exercise project progress"},
    )
    tasks = []
    for sequence in (1, 2):
        _, task = api.call(
            "POST",
            f"/plans/{plan['id']}/tasks",
            {
                "agent_id": "support",
                "title": f"Workflow task {sequence}",
                "instructions": "Fictitious task for the workflow check.",
                "priority": "normal",
                "risk_level": "green",
                "sequence": sequence,
            },
        )
        tasks.append(task)
    status, _ = api.call("POST", f"/plans/{plan['id']}/approve")
    check(status == 200, "approve the plan", str(status))
    for task in tasks:
        status, _ = api.call(
            "POST", f"/projects/{project['id']}/tasks", {"resource_id": task["id"]}
        )
        check(
            status in (200, 201, 204),
            f"link {task['title']} to the project",
            str(status),
        )
    _, detail = api.call("GET", f"/projects/{project['id']}")
    linked = {item["id"] for item in detail.get("tasks", [])}
    check(
        linked == {task["id"] for task in tasks},
        "project lists both tasks",
        str(len(linked)),
    )
    check(detail.get("progress_percentage") == 0, "progress starts at 0 %")
    first = tasks[0]["id"]
    for target in ("ready", "running", "completed"):
        status, _ = api.call(
            "POST", f"/tasks/{first}/transition", {"status": target}
        )
        if status != 200 and target == "ready":
            continue  # already ready after approval
        check(status == 200, f"task 1 → {target}", str(status) if status != 200 else "")
    _, detail = api.call("GET", f"/projects/{project['id']}")
    check(
        detail.get("progress_percentage") == 50,
        "progress follows completion (1 of 2 = 50 %)",
        str(detail.get("progress_percentage")),
    )


def scheduled_automation(api: Api, stamp: str, wait_seconds: int) -> None:
    due = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    status, automation = api.call(
        "POST",
        "/automations",
        {
            "name": f"Workflow schedule {stamp}",
            "trigger_type": "schedule",
            "trigger_config": {"interval_minutes": 1440},
            "next_run_at": due,
            "command_template": "Prepare the fictitious workflow-check report.",
        },
    )
    check(status == 201, "create a due scheduled automation", str(status))
    if status != 201:
        return
    deadline = time.time() + wait_seconds
    runs: list[dict] = []
    while time.time() < deadline:
        _, listing = api.call(
            "GET", f"/automations/runs?automation_id={automation['id']}"
        )
        runs = [
            item
            for item in (listing or {}).get("runs", [])
            if item["automation_id"] == automation["id"]
        ]
        if runs:
            break
        time.sleep(3)
    check(len(runs) == 1, "the scheduler ran it on its own", f"{len(runs)} run(s)")
    if runs:
        check(runs[0]["command_id"] is not None, "the run created a command")
        status, _ = api.call("GET", f"/commands/{runs[0]['command_id']}")
        check(status == 200, "the command exists in the workspace", str(status))
    _, after = api.call("GET", f"/automations/{automation['id']}")
    advanced = after.get("next_run_at") and after["next_run_at"] > due
    check(bool(advanced), "next run moved forward", str(after.get("next_run_at")))
    time.sleep(5)
    _, listing = api.call("GET", f"/automations/runs?automation_id={automation['id']}")
    count = sum(
        1
        for item in (listing or {}).get("runs", [])
        if item["automation_id"] == automation["id"]
    )
    check(count == 1, "no duplicate run", str(count))
    api.call("POST", f"/automations/{automation['id']}/pause")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--accounts", required=True, type=Path)
    parser.add_argument("--wait", type=int, default=90)
    args = parser.parse_args()
    api = Api(args.api)
    email, password = owner_credentials(args.accounts)
    status, auth = api.call(
        "POST", "/auth/login", {"email": email, "password": password}
    )
    if status != 200:
        raise SystemExit(f"login failed: {status}")
    api.token = auth["access_token"]
    stamp = datetime.now(UTC).strftime("%H%M%S")
    print("== Projects and tasks")
    projects_and_tasks(api, stamp)
    print("== Scheduled automations")
    scheduled_automation(api, stamp, args.wait)
    print(f"\n{'ALL PASSED' if not FAILURES else f'{len(FAILURES)} FAILED'}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
