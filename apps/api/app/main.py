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
from app.execution.exceptions import (
    ExecutionError,
    ToolInputValidationError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolVersionError,
)

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


@app.exception_handler(ExecutionError)
async def execution_error_handler(_request: Request, error: ExecutionError) -> JSONResponse:
    if isinstance(error, ToolNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ToolPermissionError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, (ToolInputValidationError, ToolVersionError)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(error, ToolTimeoutError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_409_CONFLICT
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service": "kiko-api", "message": "Kiko — Pixart AI Operating System"}


app.include_router(api_router)
