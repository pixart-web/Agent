from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.services.rate_limiter import (
    RateLimiter,
    RateLimiterUnavailableError,
    get_rate_limiter,
)


def auth_rate_limit(endpoint: str) -> Callable[..., None]:
    def dependency(
        request: Request,
        limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    ) -> None:
        ip_address = request.client.host if request.client else "unknown"
        try:
            decision = limiter.check(endpoint, ip_address)
        except RateLimiterUnavailableError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication temporarily unavailable",
            ) from error

        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts",
                headers={"Retry-After": str(decision.retry_after)},
            )

    return dependency
