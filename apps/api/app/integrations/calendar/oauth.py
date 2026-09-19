from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.integrations.calendar.errors import (
    CalendarAuthenticationError,
    CalendarTransientError,
)
from app.integrations.oauth_state import (
    IntegrationOAuthStateCodec,
    InvalidOAuthStateError,
    OAuthStateClaims,
)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
OAUTH_PROVIDER = "google_calendar"
OAUTH_PURPOSE = "calendar_oauth"
INVALID_STATE_MESSAGE = "OAuth authorization could not be validated"


class GoogleCalendarOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def scopes(self) -> list[str]:
        values = ["https://www.googleapis.com/auth/calendar.readonly"]
        if self.settings.calendar_write_enabled:
            values.append("https://www.googleapis.com/auth/calendar.events")
        return values

    def issue_state(
        self,
        user_id: UUID,
        *,
        state_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> str:
        now = datetime.now(UTC)
        return IntegrationOAuthStateCodec(self.settings, OAUTH_PURPOSE).issue(
            user_id,
            state_id or uuid4(),
            now,
            expires_at
            or now + timedelta(minutes=self.settings.calendar_oauth_state_expire_minutes),
        )

    def decode_state(self, state: str) -> OAuthStateClaims:
        try:
            return IntegrationOAuthStateCodec(self.settings, OAUTH_PURPOSE).decode(state)
        except InvalidOAuthStateError as error:
            raise CalendarAuthenticationError(INVALID_STATE_MESSAGE) from error

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_calendar_redirect_uri,
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
                "redirect_uri": self.settings.google_calendar_redirect_uri,
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
            raise CalendarAuthenticationError("Google token response has no access token")
        return token

    def revoke(self, refresh_token: str) -> None:
        try:
            response = httpx.post(
                REVOKE_URL,
                params={"token": refresh_token},
                timeout=self.settings.calendar_api_timeout_seconds,
            )
        except httpx.HTTPError:
            return
        if response.status_code not in {200, 400}:
            raise CalendarTransientError("Google credential revocation failed")

    def _token(self, data: dict[str, object]) -> dict[str, object]:
        try:
            response = httpx.post(
                TOKEN_URL, data=data, timeout=self.settings.calendar_api_timeout_seconds
            )
        except httpx.HTTPError as error:
            raise CalendarTransientError("Google OAuth service is unavailable") from error
        if response.status_code >= 400:
            raise CalendarAuthenticationError("Google OAuth authorization failed")
        payload = response.json()
        if not isinstance(payload, dict):
            raise CalendarAuthenticationError("Google OAuth response is invalid")
        return payload
