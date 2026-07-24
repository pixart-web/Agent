import hashlib
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


class RateLimiterUnavailableError(Exception):
    """Raised when fail-closed rate limiting cannot reach Redis."""


class RateLimiter:
    def check(self, endpoint: str, ip_address: str) -> RateLimitDecision:
        settings = get_settings()
        if not settings.auth_rate_limit_enabled:
            return RateLimitDecision(allowed=True)

        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.service_connect_timeout_seconds,
            socket_timeout=settings.service_connect_timeout_seconds,
        )
        ip_digest = hashlib.sha256(ip_address.encode("utf-8")).hexdigest()[:24]
        key = f"agent:auth-rate:{endpoint}:{ip_digest}"

        try:
            created = client.set(
                key,
                1,
                ex=settings.auth_rate_limit_window_seconds,
                nx=True,
            )
            if created:
                return RateLimitDecision(allowed=True)

            count = int(client.incr(key))
            ttl = max(int(client.ttl(key)), 1)
            return RateLimitDecision(
                allowed=count <= settings.auth_rate_limit_requests,
                retry_after=ttl,
            )
        except RedisError as error:
            if settings.auth_rate_limit_fail_open:
                return RateLimitDecision(allowed=True)
            raise RateLimiterUnavailableError from error
        finally:
            client.close()


def get_rate_limiter() -> RateLimiter:
    return RateLimiter()
