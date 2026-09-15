from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
import jwt

from app.core.config import Settings
from app.integrations.email.errors import EmailAuthenticationError, EmailTransientError

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
OAUTH_PROVIDER = "gmail"
OAUTH_PURPOSE = "email_oauth"
INVALID_STATE_MESSAGE = "OAuth authorization could not be validated"


@dataclass(frozen=True)
class OAuthStateClaims:
    user_id: UUID
    state_id: UUID
    expires_at: datetime


class GmailOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def scopes(self) -> list[str]:
        values = ["https://www.googleapis.com/auth/gmail.readonly"]
        if self.settings.email_send_enabled:
            values.append("https://www.googleapis.com/auth/gmail.send")
        if self.settings.email_mark_read_enabled:
            values.append("https://www.googleapis.com/auth/gmail.modify")
        return values

    def issue_state(
        self,
        user_id: UUID,
        *,
        state_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(user_id),
                "purpose": OAUTH_PURPOSE,
                "jti": str(state_id or uuid4()),
                "iat": now,
                "exp": expires_at
                or now + timedelta(minutes=self.settings.email_oauth_state_expire_minutes),
            },
            self.settings.auth_secret_key,
            algorithm=self.settings.auth_algorithm,
        )

    def decode_state(self, state: str) -> OAuthStateClaims:
        try:
            claims = jwt.decode(
                state,
                self.settings.auth_secret_key,
                algorithms=[self.settings.auth_algorithm],
                options={"require": ["sub", "purpose", "jti", "iat", "exp"]},
            )
            if claims.get("purpose") != OAUTH_PURPOSE:
                raise ValueError
            expires_at = datetime.fromtimestamp(float(claims["exp"]), UTC)
            return OAuthStateClaims(
                user_id=UUID(str(claims["sub"])),
                state_id=UUID(str(claims["jti"])),
                expires_at=expires_at,
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise EmailAuthenticationError(INVALID_STATE_MESSAGE) from error

    def state_user(self, state: str) -> UUID:
        return self.decode_state(state).user_id

    def validate_state(self, state: str, user_id: UUID) -> None:
        if self.decode_state(state).user_id != user_id:
            raise EmailAuthenticationError(INVALID_STATE_MESSAGE)

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict[str, object]:
        return self._token(
            {
                "code": code,
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret.get_secret_value(),
                "redirect_uri": self.settings.google_redirect_uri,
                "grant_type": "authorization_code",
            }
        )

    def refresh(self, refresh_token: str) -> str:
        payload = self._token(
            {
                "refresh_token": refresh_token,
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret.get_secret_value(),
                "grant_type": "refresh_token",
            }
        )
        token = payload.get("access_token")
        if not isinstance(token, str):
            raise EmailAuthenticationError("Google token response has no access token")
        return token

    def revoke(self, refresh_token: str) -> None:
        try:
            response = httpx.post(
                REVOKE_URL,
                params={"token": refresh_token},
                timeout=self.settings.email_api_timeout_seconds,
            )
        except httpx.HTTPError:
            return
        if response.status_code not in {200, 400}:
            raise EmailTransientError("Google credential revocation failed")

    def _token(self, data: dict[str, object]) -> dict[str, object]:
        try:
            response = httpx.post(
                TOKEN_URL, data=data, timeout=self.settings.email_api_timeout_seconds
            )
        except httpx.HTTPError as error:
            raise EmailTransientError("Google OAuth service is unavailable") from error
        if response.status_code >= 400:
            raise EmailAuthenticationError("Google OAuth authorization failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise EmailAuthenticationError("Google OAuth response is invalid")
        return payload
