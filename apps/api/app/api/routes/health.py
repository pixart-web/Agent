from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.schemas.readiness import ReadinessResponse
from app.services.readiness_service import ReadinessService, get_readiness_service

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "agent-api"}


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def ready(
    service: Annotated[ReadinessService, Depends(get_readiness_service)],
) -> ReadinessResponse | JSONResponse:
    result = service.check()
    if result.status == "ready":
        return result

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=result.model_dump(),
    )
