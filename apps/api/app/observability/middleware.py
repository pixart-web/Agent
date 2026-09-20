import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.observability.metrics import MetricsRegistry

logger = logging.getLogger("kiko.http")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        registry: MetricsRegistry,
        production: bool = False,
    ) -> None:
        super().__init__(app)
        self.registry = registry
        self.production = production

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied_id = request.headers.get("x-request-id", "")
        request_id = supplied_id if REQUEST_ID_PATTERN.fullmatch(supplied_id) else str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            self._record(request, request_id, status_code, started, "error")
            raise
        self._record(request, request_id, status_code, started, "info")
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if self.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def _record(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        started: float,
        level: str,
    ) -> None:
        duration = perf_counter() - started
        route_object = request.scope.get("route")
        route = getattr(route_object, "path", "unmatched")
        if route != "/metrics":
            self.registry.observe(request.method, route, status_code, duration)
        event = json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "route": route,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 3),
            },
            separators=(",", ":"),
        )
        getattr(logger, level)(event)
