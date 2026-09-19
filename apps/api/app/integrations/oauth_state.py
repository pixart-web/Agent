"""Shared signed OAuth state claims used with persisted one-shot nonces."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import jwt

from app.core.config import Settings


class InvalidOAuthStateError(ValueError):
    """Raised when a signed OAuth state cannot be trusted."""


@dataclass(frozen=True)
class OAuthStateClaims:
    user_id: UUID
    state_id: UUID
    expires_at: datetime


class IntegrationOAuthStateCodec:
    def __init__(self, settings: Settings, purpose: str) -> None:
        self.settings = settings
        self.purpose = purpose

    def issue(
        self,
        user_id: UUID,
        state_id: UUID,
        issued_at: datetime,
        expires_at: datetime,
    ) -> str:
        return jwt.encode(
            {
                "sub": str(user_id),
                "purpose": self.purpose,
                "jti": str(state_id),
                "iat": issued_at,
                "exp": expires_at,
            },
            self.settings.auth_secret_key,
            algorithm=self.settings.auth_algorithm,
        )

    def decode(self, state: str) -> OAuthStateClaims:
        try:
            claims = jwt.decode(
                state,
                self.settings.auth_secret_key,
                algorithms=[self.settings.auth_algorithm],
                options={"require": ["sub", "purpose", "jti", "iat", "exp"]},
            )
            if claims.get("purpose") != self.purpose:
                raise ValueError
            return OAuthStateClaims(
                user_id=UUID(str(claims["sub"])),
                state_id=UUID(str(claims["jti"])),
                expires_at=datetime.fromtimestamp(float(claims["exp"]), UTC),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise InvalidOAuthStateError from error
