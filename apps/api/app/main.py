from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.exceptions import (
    AIConfigurationError,
    AIError,
    AIInvalidResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.web_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AIError)
async def ai_error_handler(_request: Request, error: AIError) -> JSONResponse:
    if isinstance(
        error, (AIProviderTimeoutError, AIProviderUnavailableError, AIConfigurationError)
    ):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, AIInvalidResponseError):
        status_code = status.HTTP_502_BAD_GATEWAY
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(error) or "Supervisor planning failed"},
    )


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service": "agent-api", "message": "Pixart Agent API"}


app.include_router(api_router)
