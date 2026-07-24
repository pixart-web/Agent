from datetime import timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings
from app.core.time import utc_now


class AccessTokenError(Exception):
    """Raised when an access token cannot be trusted."""


def create_access_token(user_id: UUID, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    issued_at = utc_now()
    expires_at = issued_at + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
    )


def decode_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=[settings.auth_algorithm],
            options={"require": ["sub", "iat", "exp", "type"]},
        )
        if payload.get("type") != "access":
            raise AccessTokenError
        return UUID(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError, AccessTokenError) as error:
        raise AccessTokenError from error
