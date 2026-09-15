import json
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken

from app.integrations.email.errors import EmailAuthenticationError


class SecretStore(Protocol):
    def encrypt(self, value: dict[str, object]) -> str: ...
    def decrypt(self, value: str) -> dict[str, object]: ...


class FernetSecretStore:
    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, TypeError) as error:
            raise EmailAuthenticationError("Invalid integration encryption key") from error

    def encrypt(self, value: dict[str, object]) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        return self._fernet.encrypt(raw).decode("ascii")

    def decrypt(self, value: str) -> dict[str, object]:
        try:
            decoded = self._fernet.decrypt(value.encode("ascii"))
            payload = json.loads(decoded)
        except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as error:
            raise EmailAuthenticationError(
                "Stored email credentials cannot be decrypted"
            ) from error
        if not isinstance(payload, dict):
            raise EmailAuthenticationError("Stored email credentials are invalid")
        return payload
