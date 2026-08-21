from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_active_user
from app.core.config import Settings, get_settings
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.user import User

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
