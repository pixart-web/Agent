from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_cookies import REFRESH_COOKIE_NAME
from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.main import app
from app.models.account_token import AccountToken
from app.models.refresh_token import RefreshToken
from app.models.transactional_email import TransactionalEmailOutbox
from app.models.user import User
from app.security.access_tokens import create_access_token
from app.security.account_tokens import decrypt_email_payload, hash_account_token
from app.security.email import normalize_email
from app.security.refresh_tokens import hash_refresh_token
from app.services.rate_limiter import (
    RateLimitDecision,
    RateLimiter,
    get_rate_limiter,
)
from app.services.refresh_token_cleanup import cleanup_refresh_tokens

REGISTER_PAYLOAD = {
    "email": "User@Example.com",
    "password": "securePassword123",
    "full_name": "User Name",
    "terms_accepted": True,
    "privacy_accepted": True,
}


def register(client: TestClient, **overrides: str) -> tuple[dict[str, object], str]:
    payload = {**REGISTER_PAYLOAD, **overrides}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 202
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get(REFRESH_COOKIE_NAME)
    assert token is not None
    return login_response.json(), token


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def token_rows(db_session: Session) -> list[RefreshToken]:
    return list(db_session.scalars(select(RefreshToken)))


def test_register_normalizes_email_and_hides_secrets(
    client: TestClient,
    db_session: Session,
) -> None:
    body, raw_refresh = register(client)

    assert body["user"]["email"] == "user@example.com"
    assert "password" not in str(body).lower()
    user = db_session.scalar(select(User))
    assert user is not None
    assert user.email == "user@example.com"
    assert user.password_hash != REGISTER_PAYLOAD["password"]
    refresh = token_rows(db_session)[0]
    assert refresh.token_hash == hash_refresh_token(raw_refresh)
    assert refresh.token_hash != raw_refresh


def test_duplicate_email_does_not_enumerate_account(client: TestClient) -> None:
    first = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    duplicate = client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": "USER@example.com"},
    )
    assert first.status_code == duplicate.status_code == 202
    assert first.json() == duplicate.json()


def test_resend_verification_does_not_enumerate_or_reveal_cooldown(
    client: TestClient,
) -> None:
    settings = get_settings()
    previous = settings.auth_require_email_verification
    settings.auth_require_email_verification = True
    try:
        assert client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD).status_code == 202
        existing = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": " USER@example.com "},
        )
        missing = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "missing@example.com"},
        )
        assert existing.status_code == missing.status_code == 200
        assert existing.json() == missing.json()
    finally:
        settings.auth_require_email_verification = previous


def test_registration_requires_legal_acceptance(client: TestClient) -> None:
    for field in ("terms_accepted", "privacy_accepted"):
        response = client.post(
            "/api/v1/auth/register",
            json={**REGISTER_PAYLOAD, field: False},
        )
        assert response.status_code == 422


def test_verified_identity_and_password_reset_lifecycle(
    client: TestClient,
    db_session: Session,
) -> None:
    settings = get_settings()
    previous = settings.auth_require_email_verification
    settings.auth_require_email_verification = True
    try:
        registered = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert registered.status_code == 202
        user = db_session.scalar(select(User))
        assert user is not None and user.email_verified_at is None

        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
        )
        assert blocked.status_code == 403

        verification_email = db_session.scalar(
            select(TransactionalEmailOutbox).where(
                TransactionalEmailOutbox.template == "email_verification"
            )
        )
        verification_token = db_session.scalar(
            select(AccountToken).where(AccountToken.purpose == "email_verification")
        )
        assert verification_email is not None and verification_token is not None
        payload = decrypt_email_payload(
            verification_email.encrypted_payload,
            settings.auth_secret_key,
        )
        raw_verification = payload["token"]
        assert verification_token.token_hash == hash_account_token(raw_verification)
        assert raw_verification not in verification_email.encrypted_payload

        verified = client.post(
            "/api/v1/auth/verify-email",
            json={"token": raw_verification},
        )
        assert verified.status_code == 200
        assert (
            client.post("/api/v1/auth/verify-email", json={"token": raw_verification}).status_code
            == 400
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
        )
        assert login_response.status_code == 200

        requested = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": REGISTER_PAYLOAD["email"]},
        )
        assert requested.status_code == 200
        reset_email = db_session.scalar(
            select(TransactionalEmailOutbox)
            .where(TransactionalEmailOutbox.template == "password_reset")
            .order_by(TransactionalEmailOutbox.created_at.desc())
        )
        assert reset_email is not None
        reset_token = decrypt_email_payload(
            reset_email.encrypted_payload,
            settings.auth_secret_key,
        )["token"]
        reset = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": reset_token, "password": "newSecurePassword456"},
        )
        assert reset.status_code == 200
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": REGISTER_PAYLOAD["email"],
                    "password": REGISTER_PAYLOAD["password"],
                },
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": REGISTER_PAYLOAD["email"], "password": "newSecurePassword456"},
            ).status_code
            == 200
        )
    finally:
        settings.auth_require_email_verification = previous


def test_normalize_email_strips_and_lowercases() -> None:
    assert normalize_email("  User@Example.com  ") == "user@example.com"


@pytest.mark.parametrize(
    "password",
    ["short1", "onlylettersxx", "1234567890"],
)
def test_invalid_password_is_rejected(client: TestClient, password: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "password": password},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "email",
    [
        "User@Example.com",
        "user@example.com",
        "  user@example.com  ",
        "uSeR@eXaMpLe.CoM",
    ],
)
def test_login_accepts_normalized_email_capitalization(
    client: TestClient,
    email: str,
) -> None:
    register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securePassword123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "user@example.com"


def test_login_updates_last_login(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "securePassword123"},
    )

    assert response.status_code == 200
    user = db_session.scalar(select(User))
    assert user is not None
    assert user.last_login_at is not None


def test_update_profile_and_change_password_revoke_sessions(client: TestClient) -> None:
    body, _ = register(client)
    headers = bearer(str(body["access_token"]))

    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"full_name": "  Updated   Name  "},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Name"

    wrong = client.post(
        "/api/v1/auth/password/change",
        headers=headers,
        json={"current_password": "wrong", "new_password": "newSecurePassword456"},
    )
    assert wrong.status_code == 400

    changed = client.post(
        "/api/v1/auth/password/change",
        headers=headers,
        json={
            "current_password": REGISTER_PAYLOAD["password"],
            "new_password": "newSecurePassword456",
        },
    )
    assert changed.status_code == 204
    assert REFRESH_COOKIE_NAME not in changed.cookies
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER_PAYLOAD["email"], "password": "newSecurePassword456"},
        ).status_code
        == 200
    )


def test_invalid_login_errors_are_identical(client: TestClient) -> None:
    register(client)
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "securePassword123"},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrongPassword123"},
    )

    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json() == {"detail": "Invalid email or password"}


def test_me_requires_and_accepts_access_token(client: TestClient) -> None:
    body, _ = register(client)

    missing = client.get("/api/v1/auth/me")
    authenticated = client.get(
        "/api/v1/auth/me",
        headers=bearer(str(body["access_token"])),
    )

    assert missing.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated.json()["email"] == "user@example.com"


def test_me_rejects_expired_token(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    user = db_session.scalar(select(User))
    assert user is not None
    expired = create_access_token(user.id, expires_delta=timedelta(seconds=-1))

    response = client.get("/api/v1/auth/me", headers=bearer(expired))
    assert response.status_code == 401


def test_me_rejects_inactive_user(
    client: TestClient,
    db_session: Session,
) -> None:
    body, _ = register(client)
    user = db_session.scalar(select(User))
    assert user is not None
    user.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers=bearer(str(body["access_token"])),
    )
    assert response.status_code == 403


def test_refresh_rotates_token(client: TestClient, db_session: Session) -> None:
    _, old_raw = register(client)
    response = client.post("/api/v1/auth/refresh")
    new_raw = response.cookies.get(REFRESH_COOKIE_NAME)

    assert response.status_code == 200
    assert new_raw is not None and new_raw != old_raw
    rows = token_rows(db_session)
    old = next(row for row in rows if row.token_hash == hash_refresh_token(old_raw))
    new = next(row for row in rows if row.token_hash == hash_refresh_token(new_raw))
    assert old.revoked_at is not None
    assert old.replaced_by_id == new.id
    assert old.family_id == new.family_id


@pytest.mark.parametrize("state", ["expired", "revoked"])
def test_refresh_rejects_unusable_token(
    client: TestClient,
    db_session: Session,
    state: str,
) -> None:
    _, raw = register(client)
    token = token_rows(db_session)[0]
    if state == "expired":
        token.expires_at = utc_now() - timedelta(minutes=1)
    else:
        token.revoked_at = utc_now()
    db_session.commit()
    client.cookies.set(
        REFRESH_COOKIE_NAME,
        raw,
        path="/api/v1/auth",
    )

    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_refresh_reuse_revokes_family(
    client: TestClient,
    db_session: Session,
) -> None:
    _, original = register(client)
    rotated = client.post("/api/v1/auth/refresh")
    replacement = rotated.cookies.get(REFRESH_COOKIE_NAME)
    assert replacement is not None

    client.cookies.set(
        REFRESH_COOKIE_NAME,
        original,
        path="/api/v1/auth",
    )
    reused = client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401

    rows = token_rows(db_session)
    assert len({row.family_id for row in rows}) == 1
    assert all(row.revoked_at is not None for row in rows)

    client.cookies.set(
        REFRESH_COOKIE_NAME,
        replacement,
        path="/api/v1/auth",
    )
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_is_idempotent_and_revokes_token(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    first = client.post("/api/v1/auth/logout")
    second = client.post("/api/v1/auth/logout")

    assert first.status_code == second.status_code == 204
    assert token_rows(db_session)[0].revoked_at is not None


def test_session_inventory_and_revocation_are_owner_scoped(
    client: TestClient,
    db_session: Session,
) -> None:
    first, _ = register(client)
    second_login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "securePassword123"},
        headers={"User-Agent": "second-device"},
    )
    headers = bearer(second_login.json()["access_token"])
    sessions = client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions.status_code == 200
    assert len(sessions.json()) == 2
    assert sum(item["current"] for item in sessions.json()) == 1

    non_current = next(item for item in sessions.json() if not item["current"])
    revoked = client.delete(f"/api/v1/auth/sessions/{non_current['id']}", headers=headers)
    assert revoked.status_code == 204
    assert len(client.get("/api/v1/auth/sessions", headers=headers).json()) == 1

    unknown = client.delete(
        "/api/v1/auth/sessions/00000000-0000-0000-0000-000000000001",
        headers=headers,
    )
    assert unknown.status_code == 404
    assert client.delete("/api/v1/auth/sessions", headers=headers).status_code == 204
    assert all(item.revoked_at is not None for item in token_rows(db_session))
    assert first["user"]["email"] == "user@example.com"


class RejectAllRateLimiter(RateLimiter):
    def check(self, endpoint: str, ip_address: str) -> RateLimitDecision:
        return RateLimitDecision(allowed=False, retry_after=37)


def test_rate_limit_returns_retry_after(
    client: TestClient,
) -> None:
    previous_override = app.dependency_overrides[get_rate_limiter]
    app.dependency_overrides[get_rate_limiter] = lambda: RejectAllRateLimiter()
    try:
        response = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    finally:
        app.dependency_overrides[get_rate_limiter] = previous_override

    assert response.status_code == 429
    assert response.headers["retry-after"] == "37"


def test_cleanup_removes_expired_and_old_revoked_tokens(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client)
    first = token_rows(db_session)[0]
    first.expires_at = utc_now() - timedelta(days=1)
    db_session.commit()

    register(
        client,
        email="second@example.com",
        full_name="Second User",
    )
    second = token_rows(db_session)[1]
    second.revoked_at = utc_now() - timedelta(days=10)
    db_session.commit()

    assert cleanup_refresh_tokens(db_session, retention_days=7) == 2
    assert token_rows(db_session) == []


def test_production_rejects_insecure_example_settings() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            auth_secret_key="development-secret-change-me-123456789",
            auth_cookie_secure=False,
        )


def test_cors_credentials_reject_wildcard_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(web_origins="*")
