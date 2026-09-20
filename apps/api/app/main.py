from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.ai.exceptions import (
    AIConfigurationError,
    AIError,
    AIInvalidResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.api.router import api_router
from app.core.config import get_settings
from app.crm.errors import CrmNotFoundError
from app.execution.exceptions import (
    ExecutionError,
    ToolInputValidationError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolVersionError,
)
from app.integrations.calendar.errors import (
    CalendarAuthenticationError,
    CalendarNotFoundError,
    CalendarRateLimitError,
    CalendarTimeoutError,
    CalendarTransientError,
)
from app.integrations.email.errors import (
    EmailAuthenticationError,
    EmailNotFoundError,
    EmailRateLimitError,
    EmailTransientError,
)
from app.marketing.errors import MarketingNotFoundError
from app.observability.metrics import metrics
from app.observability.middleware import ObservabilityMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if settings.app_env.lower() == "production" else "/docs",
    redoc_url=None if settings.app_env.lower() == "production" else "/redoc",
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(
    ObservabilityMiddleware,
    registry=metrics,
    production=settings.app_env.lower() == "production",
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
    if isinstance(
        error,
        (
            ToolNotFoundError,
            EmailNotFoundError,
            CalendarNotFoundError,
            CrmNotFoundError,
            MarketingNotFoundError,
        ),
    ):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, (EmailAuthenticationError, CalendarAuthenticationError)):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(error, ToolPermissionError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, (ToolInputValidationError, ToolVersionError)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(
        error,
        (
            ToolTimeoutError,
            EmailRateLimitError,
            EmailTransientError,
            CalendarRateLimitError,
            CalendarTimeoutError,
            CalendarTransientError,
        ),
    ):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_409_CONFLICT
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service": "kiko-api", "message": "Kiko — Pixart AI Operating System"}


app.include_router(api_router)
