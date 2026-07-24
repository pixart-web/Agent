from collections.abc import Callable

from app.db.health import database_is_healthy, redis_is_healthy
from app.schemas.readiness import ReadinessResponse, ServiceHealth

HealthCheck = Callable[[], bool]


class ReadinessService:
    def __init__(
        self,
        database_check: HealthCheck = database_is_healthy,
        redis_check: HealthCheck = redis_is_healthy,
    ) -> None:
        self.database_check = database_check
        self.redis_check = redis_check

    @staticmethod
    def _safe_check(check: HealthCheck) -> bool:
        try:
            return check()
        except Exception:
            return False

    def check(self) -> ReadinessResponse:
        database_healthy = self._safe_check(self.database_check)
        redis_healthy = self._safe_check(self.redis_check)
        is_ready = database_healthy and redis_healthy

        return ReadinessResponse(
            status="ready" if is_ready else "unavailable",
            services=ServiceHealth(
                database="healthy" if database_healthy else "unavailable",
                redis="healthy" if redis_healthy else "unavailable",
            ),
        )


def get_readiness_service() -> ReadinessService:
    return ReadinessService()
