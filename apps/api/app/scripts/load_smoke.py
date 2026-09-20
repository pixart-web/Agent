import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import httpx

from app.operations.load_probe import is_loopback_url, percentile


def request_once(url: str, timeout: float) -> tuple[int, float]:
    started = perf_counter()
    response = httpx.get(url, timeout=timeout)
    return response.status_code, (perf_counter() - started) * 1000


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded health endpoint load smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=100, choices=range(1, 10_001))
    parser.add_argument("--concurrency", type=int, default=10, choices=range(1, 201))
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()
    if not is_loopback_url(args.base_url) and not args.allow_remote:
        raise SystemExit("Remote load probes require explicit --allow-remote")
    url = args.base_url.rstrip("/") + "/health"
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(
            executor.map(lambda _: request_once(url, args.timeout), range(args.requests))
        )
    latencies = [latency for _, latency in results]
    errors = sum(status != 200 for status, _ in results)
    report = {
        "requests": len(results),
        "errors": errors,
        "error_rate": errors / len(results),
        "p50_ms": percentile(latencies, 0.50),
        "p95_ms": percentile(latencies, 0.95),
        "p99_ms": percentile(latencies, 0.99),
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
