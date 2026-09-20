from collections import defaultdict
from threading import Lock


class MetricsRegistry:
    """Small dependency-free per-process metrics registry."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self._duration_seconds: dict[tuple[str, str], float] = defaultdict(float)

    def observe(self, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        key = (method, route, status_code)
        with self._lock:
            self._requests[key] += 1
            self._duration_seconds[(method, route)] += duration_seconds

    @staticmethod
    def _label(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def render(self) -> str:
        lines = [
            "# HELP kiko_http_requests_total HTTP requests handled by this process.",
            "# TYPE kiko_http_requests_total counter",
        ]
        with self._lock:
            requests = sorted(self._requests.items())
            durations = sorted(self._duration_seconds.items())
        for (method, route, status_code), count in requests:
            labels = (
                f'method="{self._label(method)}",route="{self._label(route)}",'
                f'status="{status_code}"'
            )
            lines.append(f"kiko_http_requests_total{{{labels}}} {count}")
        lines.extend(
            (
                "# HELP kiko_http_request_duration_seconds_sum Total request duration.",
                "# TYPE kiko_http_request_duration_seconds_sum counter",
            )
        )
        for (method, route), duration in durations:
            labels = f'method="{self._label(method)}",route="{self._label(route)}"'
            lines.append(f"kiko_http_request_duration_seconds_sum{{{labels}}} {duration:.6f}")
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
