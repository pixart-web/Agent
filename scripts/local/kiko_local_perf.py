"""Bounded performance probe for the local Kiko API (loopback only, fictitious data).

Measures latency of the endpoints the desktop app calls most, sequentially and with modest
concurrency, plus repeated login/logout. Small request counts: this is a measurement on the
owner's Mac, not a load test. Invoked by `scripts/local/kiko-local.sh perf`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiko_local_ai_eval as ai
import kiko_local_smoke as smoke

ENDPOINTS = [
    "/auth/me",
    "/workspaces/onboarding",
    "/commands?limit=50",
    "/tasks?limit=100",
    "/projects",
    "/crm/contacts",
    "/notifications",
    "/approvals",
    "/conversations",
    "/executions",
]


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 1)


def timed_call(api: smoke.Api, path: str, token: str) -> tuple[int, float]:
    started = time.perf_counter()
    status, _ = api.call("GET", path, token=token)
    return status, (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--mailpit", required=True)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()
    api = smoke.Api(args.api)
    token, email = ai.account(api, args.mailpit, "perf")
    for index in range(20):  # some data so list endpoints are not empty
        api.call(
            "POST", "/commands", {"input": f"Perf probe command {index}"}, token=token
        )
        api.call("POST", "/projects", {"name": f"Perf project {index}"}, token=token)
        api.call(
            "POST",
            "/crm/contacts",
            {"full_name": f"Contacto Fictício {index}"},
            token=token,
        )

    report: dict[str, object] = {"samples": args.samples, "endpoints": {}}
    for path in ENDPOINTS:
        results = [timed_call(api, path, token) for _ in range(args.samples)]
        latencies = [ms for _, ms in results]
        errors = sum(status != 200 for status, _ in results)
        report["endpoints"][path] = {
            "p50_ms": pct(latencies, 0.5),
            "p95_ms": pct(latencies, 0.95),
            "max_ms": round(max(latencies), 1),
            "errors": errors,
        }
        smoke.check(
            f"GET {path}",
            errors == 0,
            f"p50 {pct(latencies, 0.5)} ms, p95 {pct(latencies, 0.95)} ms",
        )

    def burst(_: int) -> tuple[int, float]:
        return timed_call(smoke.Api(args.api), ENDPOINTS[2], token)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(burst, range(200)))
    elapsed = time.perf_counter() - started
    latencies = [ms for _, ms in results]
    errors = sum(status != 200 for status, _ in results)
    report["concurrency"] = {
        "requests": 200,
        "workers": 10,
        "errors": errors,
        "throughput_rps": round(200 / elapsed, 1),
        "p50_ms": pct(latencies, 0.5),
        "p95_ms": pct(latencies, 0.95),
    }
    smoke.check(
        "200 requests at concurrency 10",
        errors == 0,
        f"{report['concurrency']['throughput_rps']} req/s, p95 {pct(latencies, 0.95)} ms",
    )

    state = Path(args.state)
    # repeated login/logout (stays under the 10/minute auth rate limit)
    logins: list[float] = []
    for _ in range(5):
        fresh = smoke.Api(args.api)
        started = time.perf_counter()
        fresh.call(
            "POST", "/auth/login", {"email": email, "password": "wrong-password-1"}
        )
        logins.append((time.perf_counter() - started) * 1000)
    report["login_rejection_ms_p50"] = pct(logins, 0.5)
    smoke.check(
        "invalid login answered (password hashing cost)",
        True,
        f"p50 {pct(logins, 0.5)} ms",
    )

    state.mkdir(parents=True, exist_ok=True)
    out = state / f"perf-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2))
    failed = [n for n, ok, _ in smoke.results if not ok]
    print(
        f"\n{len(smoke.results) - len(failed)}/{len(smoke.results)} checks passed · {out}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
