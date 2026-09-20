from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.observability.metrics import metrics

router = APIRouter(tags=["system"])


@router.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
def prometheus_metrics(
    authorization: Annotated[str | None, Header()] = None,
) -> PlainTextResponse:
    settings = get_settings()
    if not settings.observability_metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    configured = settings.observability_metrics_token
    if configured is not None:
        expected = f"Bearer {configured.get_secret_value()}"
        if authorization is None or not compare_digest(authorization, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")
