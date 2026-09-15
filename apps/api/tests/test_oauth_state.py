from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.integrations.email.oauth import (
    INVALID_STATE_MESSAGE,
    OAUTH_PROVIDER,
    OAUTH_PURPOSE,
    GmailOAuthClient,
)
from app.integrations.email.providers.gmail import GmailProvider
from app.main import app
from app.models.integration_account import IntegrationAccount
from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.user import User
from app.repositories.integration_oauth_state_repository import (
    IntegrationOAuthStateRepository,
)
from app.services.oauth_state_cleanup import cleanup_oauth_states
from tests.test_email_integration import email_settings


def register(client: TestClient, email: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securePassword123",
            "full_name": "OAuth User",
        },
    )
    assert response.status_code == 201
    return response.json()


def bearer(auth: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['access_token']}"}


def persist_state(
    db_session: Session,
    oauth: GmailOAuthClient,
    *,
    token_user_id,
    nonce_user_id=None,
    provider: str = OAUTH_PROVIDER,
    purpose: str = OAUTH_PURPOSE,
    expires_at=None,
) -> tuple[str, IntegrationOAuthState]:
    expiration = expires_at or utc_now() + timedelta(minutes=10)
    nonce = IntegrationOAuthState(
        user_id=nonce_user_id or token_user_id,
        provider=provider,
        purpose=purpose,
        expires_at=expiration,
    )
    db_session.add(nonce)
    db_session.commit()
    return (
        oauth.issue_state(token_user_id, state_id=nonce.id, expires_at=expiration),
        nonce,
    )


def test_connect_persists_only_nonce_metadata_and_binds_signed_state(
    client: TestClient, db_session: Session
) -> None:
    settings = email_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    auth = register(client, "oauth-connect@example.com")
    user = db_session.scalar(select(User).where(User.email == "oauth-connect@example.com"))
    assert user is not None

    response = client.post("/api/v1/integrations/email/connect", headers=bearer(auth))

    assert response.status_code == 200
    authorization_url = response.json()["authorization_url"]
    state_token = parse_qs(urlparse(authorization_url).query)["state"][0]
    claims = GmailOAuthClient(settings).decode_state(state_token)
    nonce = db_session.get(IntegrationOAuthState, claims.state_id)
    assert nonce is not None
    assert nonce.user_id == user.id == claims.user_id
    assert nonce.provider == OAUTH_PROVIDER
    assert nonce.purpose == OAUTH_PURPOSE
    assert nonce.consumed_at is None
    assert state_token not in repr(nonce.__dict__)


def test_callback_consumes_state_once_before_creating_account(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = email_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    register(client, "oauth-callback@example.com")
    user = db_session.scalar(select(User).where(User.email == "oauth-callback@example.com"))
    assert user is not None
    oauth = GmailOAuthClient(settings)
    state_token, nonce = persist_state(db_session, oauth, token_user_id=user.id)
    exchanges = 0

    def exchange_code(_self: GmailOAuthClient, _code: str) -> dict[str, object]:
        nonlocal exchanges
        exchanges += 1
        return {"refresh_token": "refresh", "access_token": "access"}

    monkeypatch.setattr(GmailOAuthClient, "exchange_code", exchange_code)
    monkeypatch.setattr(
        GmailProvider, "profile", lambda _self: {"emailAddress": "support@example.com"}
    )
    monkeypatch.setattr(GmailProvider, "close", lambda _self: None)

    first = client.get(
        "/api/v1/integrations/email/callback",
        params={"code": "one-time-code", "state": state_token},
        follow_redirects=False,
    )
    second = client.get(
        "/api/v1/integrations/email/callback",
        params={"code": "replayed-code", "state": state_token},
        follow_redirects=False,
    )

    assert first.status_code == 303
    assert second.status_code == 401
    assert second.json() == {"detail": INVALID_STATE_MESSAGE}
    assert exchanges == 1
    db_session.expire_all()
    assert db_session.get(IntegrationOAuthState, nonce.id).consumed_at is not None
    assert db_session.scalar(select(func.count()).select_from(IntegrationAccount)) == 1


@pytest.mark.parametrize(
    ("variant",),
    [("unknown",), ("expired",), ("other_user",), ("provider",), ("purpose",)],
)
def test_invalid_state_returns_one_generic_error_and_never_creates_account(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
) -> None:
    settings = email_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    register(client, f"oauth-{variant}@example.com")
    register(client, f"oauth-{variant}-other@example.com")
    users = list(
        db_session.scalars(
            select(User).where(User.email.like(f"oauth-{variant}%")).order_by(User.email)
        )
    )
    token_user = next(user for user in users if user.email == f"oauth-{variant}@example.com")
    other_user = next(user for user in users if user.id != token_user.id)
    oauth = GmailOAuthClient(settings)

    if variant == "unknown":
        state_token = oauth.issue_state(token_user.id)
    else:
        expiration = utc_now() - timedelta(minutes=1) if variant == "expired" else None
        state_token, _ = persist_state(
            db_session,
            oauth,
            token_user_id=token_user.id,
            nonce_user_id=other_user.id if variant == "other_user" else None,
            provider="outlook" if variant == "provider" else OAUTH_PROVIDER,
            purpose="different" if variant == "purpose" else OAUTH_PURPOSE,
            expires_at=expiration,
        )

    monkeypatch.setattr(
        GmailOAuthClient,
        "exchange_code",
        lambda *_args: pytest.fail("invalid state reached Google token exchange"),
    )
    response = client.get(
        "/api/v1/integrations/email/callback",
        params={"code": "must-not-run", "state": state_token},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": INVALID_STATE_MESSAGE}
    assert db_session.scalar(select(func.count()).select_from(IntegrationAccount)) == 0


def test_atomic_consume_rejects_a_second_use(db_session: Session) -> None:
    auth_user = User(
        email="repository-oauth@example.com",
        password_hash="not-used",
        full_name="Repository OAuth",
    )
    db_session.add(auth_user)
    db_session.commit()
    oauth = GmailOAuthClient(email_settings())
    _, nonce = persist_state(db_session, oauth, token_user_id=auth_user.id)
    repository = IntegrationOAuthStateRepository(db_session)

    assert repository.consume(nonce.id, auth_user.id, OAUTH_PROVIDER, OAUTH_PURPOSE, utc_now())
    db_session.commit()
    assert not repository.consume(nonce.id, auth_user.id, OAUTH_PROVIDER, OAUTH_PURPOSE, utc_now())


def test_cleanup_removes_expired_and_old_consumed_states(db_session: Session) -> None:
    now = utc_now()
    auth_user = User(
        email="cleanup-oauth@example.com", password_hash="not-used", full_name="Cleanup OAuth"
    )
    db_session.add(auth_user)
    db_session.flush()
    rows = [
        IntegrationOAuthState(
            user_id=auth_user.id,
            provider=OAUTH_PROVIDER,
            purpose=OAUTH_PURPOSE,
            expires_at=now - timedelta(minutes=1),
        ),
        IntegrationOAuthState(
            user_id=auth_user.id,
            provider=OAUTH_PROVIDER,
            purpose=OAUTH_PURPOSE,
            expires_at=now + timedelta(days=1),
            consumed_at=now - timedelta(days=8),
        ),
        IntegrationOAuthState(
            user_id=auth_user.id,
            provider=OAUTH_PROVIDER,
            purpose=OAUTH_PURPOSE,
            expires_at=now + timedelta(days=1),
        ),
        IntegrationOAuthState(
            user_id=auth_user.id,
            provider=OAUTH_PROVIDER,
            purpose=OAUTH_PURPOSE,
            expires_at=now + timedelta(days=1),
            consumed_at=now - timedelta(days=1),
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()

    assert cleanup_oauth_states(db_session, retention_days=7) == 2
    remaining = set(db_session.scalars(select(IntegrationOAuthState.id)))
    assert remaining == {rows[2].id, rows[3].id}
