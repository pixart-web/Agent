from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_active_user
from app.core.config import Settings, get_settings
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.user import User
from app.schemas.codex import CodexIntegrationStatus

router = APIRouter(tags=["integrations"])


class GitHubIntegrationStatus(BaseModel):
    enabled: bool
    allowed_repositories: list[str]
    credential_configured: bool


@router.get("/integrations/github/status", response_model=GitHubIntegrationStatus)
def github_status(
    _user: Annotated[User, Depends(get_current_active_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GitHubIntegrationStatus:
    credentials = EnvironmentCredentialProvider(settings)
    return GitHubIntegrationStatus(
        enabled=settings.github_integration_enabled,
        allowed_repositories=settings.github_allowed_repository_list,
        credential_configured=credentials.configured("github"),
    )


@router.get("/integrations/codex/status", response_model=CodexIntegrationStatus)
def codex_status(
    _user: Annotated[User, Depends(get_current_active_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CodexIntegrationStatus:
    credentials = EnvironmentCredentialProvider(settings)
    return CodexIntegrationStatus(
        enabled=settings.codex_integration_enabled,
        runner=settings.codex_runner,
        allowed_repositories=settings.codex_allowed_repository_list,
        credential_configured=(
            settings.codex_credential_configured or credentials.configured("codex")
        ),
        github_credential_configured=credentials.configured("github"),
        timeout_seconds=settings.codex_timeout_seconds,
    )
