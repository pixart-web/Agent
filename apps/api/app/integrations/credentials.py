from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings, get_settings
from app.execution.exceptions import ExecutionError


class CredentialUnavailableError(ExecutionError):
    code = "credential_unavailable"


@dataclass(frozen=True)
class ServiceCredential:
    access_token: str

    def __repr__(self) -> str:
        return "ServiceCredential(access_token='[REDACTED]')"


class CredentialProvider(Protocol):
    def resolve(self, service: str) -> ServiceCredential: ...

    def configured(self, service: str) -> bool: ...


class EnvironmentCredentialProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def resolve(self, service: str) -> ServiceCredential:
        if service != "github":
            raise CredentialUnavailableError("Credential service is not supported")
        token = self.settings.github_token
        if not token:
            raise CredentialUnavailableError("GitHub credential is not configured")
        return ServiceCredential(access_token=token.get_secret_value())

    def configured(self, service: str) -> bool:
        return service == "github" and bool(self.settings.github_token)
