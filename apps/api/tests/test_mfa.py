from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_cookies import REFRESH_COOKIE_NAME
from app.core.time import utc_now
from app.models.user import User
from app.security import totp
from app.security.access_tokens import create_access_token, create_mfa_challenge_token
from tests.test_auth import REGISTER_PAYLOAD, bearer, register

LOGIN = {"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]}


def current_code(secret: str, offset_steps: int = 0) -> str:
    return totp.code_at(secret, totp.time_step(utc_now()) + offset_steps)


def enable_mfa(client: TestClient, access_token: str) -> tuple[str, list[str]]:
    setup = client.post("/api/v1/auth/mfa/setup", headers=bearer(access_token))
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/Kiko%3Auser%40example.com?")
    enabled = client.post(
        "/api/v1/auth/mfa/enable",
        headers=bearer(access_token),
        json={"code": current_code(secret)},
    )
    assert enabled.status_code == 200
    return secret, enabled.json()["recovery_codes"]


def test_totp_matches_rfc6238_reference_vector() -> None:
    # RFC 6238 appendix B, SHA-1 secret "12345678901234567890", T = 59 s -> 94287082 (8 digits).
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert totp.code_at(secret, 59 // 30) == "287082"


def test_verify_code_refuses_replay_and_out_of_window_codes() -> None:
    secret = totp.generate_secret()
    now = utc_now()
    step = totp.time_step(now)
    assert totp.verify_code(secret, totp.code_at(secret, step), now, None) == step
    assert totp.verify_code(secret, totp.code_at(secret, step), now, step) is None
    assert totp.verify_code(secret, totp.code_at(secret, step - 3), now, None) is None
    assert totp.verify_code(secret, "12ab56", now, None) is None


def test_enrolment_requires_a_valid_code_and_stores_secrets_safely(
    client: TestClient, db_session: Session
) -> None:
    body, _ = register(client)
    token = str(body["access_token"])
    assert body["user"]["mfa_enabled"] is False

    setup = client.post("/api/v1/auth/mfa/setup", headers=bearer(token)).json()
    wrong = client.post("/api/v1/auth/mfa/enable", headers=bearer(token), json={"code": "000000"})
    if wrong.status_code == 200:  # pragma: no cover - 1 in a million collision
        return
    assert wrong.status_code == 400
    assert client.get("/api/v1/auth/mfa", headers=bearer(token)).json()["setup_pending"] is True

    enabled = client.post(
        "/api/v1/auth/mfa/enable",
        headers=bearer(token),
        json={"code": current_code(setup["secret"])},
    )
    assert enabled.status_code == 200
    codes = enabled.json()["recovery_codes"]
    assert len(codes) == 10 and len(set(codes)) == 10

    user = db_session.scalar(select(User))
    assert user is not None
    db_session.refresh(user)
    assert user.mfa_enabled
    assert setup["secret"] not in (user.mfa_secret_encrypted or "")
    assert all(code not in str(user.mfa_recovery_code_hashes) for code in codes)
    status = client.get("/api/v1/auth/mfa", headers=bearer(token)).json()
    assert status == {**status, "enabled": True, "recovery_codes_remaining": 10}
    assert client.get("/api/v1/auth/me", headers=bearer(token)).json()["mfa_enabled"] is True
    again = client.post("/api/v1/auth/mfa/setup", headers=bearer(token))
    assert again.status_code == 409


def test_login_with_mfa_needs_the_second_step(client: TestClient) -> None:
    body, _ = register(client)
    secret, _codes = enable_mfa(client, str(body["access_token"]))
    client.cookies.clear()

    first = client.post("/api/v1/auth/login", json=LOGIN)
    assert first.status_code == 200
    challenge = first.json()
    assert challenge["mfa_required"] is True
    assert "access_token" not in challenge
    assert first.cookies.get(REFRESH_COOKIE_NAME) is None
    # The challenge token is not an access token.
    assert client.get("/api/v1/auth/me", headers=bearer(challenge["mfa_token"])).status_code == 401

    bad = client.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": challenge["mfa_token"], "code": "999999"}
    )
    if bad.status_code != 200:
        assert bad.status_code == 401
        assert bad.json()["detail"] == "Invalid or expired verification code"

    # The enrolment code's step is used; the next step's code is accepted (drift window).
    verified = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": challenge["mfa_token"], "code": current_code(secret, 1)},
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["mfa_enabled"] is True
    assert verified.cookies.get(REFRESH_COOKIE_NAME)
    me = client.get("/api/v1/auth/me", headers=bearer(verified.json()["access_token"]))
    assert me.status_code == 200

    replay = client.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": challenge["mfa_token"], "code": current_code(secret, 1)},
    )
    assert replay.status_code == 401


def test_recovery_codes_work_once(client: TestClient) -> None:
    body, _ = register(client)
    _secret, codes = enable_mfa(client, str(body["access_token"]))
    challenge = client.post("/api/v1/auth/login", json=LOGIN).json()["mfa_token"]

    used = client.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": codes[0].upper()}
    )
    assert used.status_code == 200
    token = used.json()["access_token"]
    assert (
        client.get("/api/v1/auth/mfa", headers=bearer(token)).json()["recovery_codes_remaining"]
        == 9
    )
    reused = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": challenge, "code": codes[0]})
    assert reused.status_code == 401


def test_challenge_token_expires_and_is_bound_to_mfa_accounts(
    client: TestClient, db_session: Session
) -> None:
    body, _ = register(client)
    user = db_session.scalar(select(User))
    assert user is not None
    plain = create_mfa_challenge_token(user.id)
    rejected = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": plain, "code": "123456"})
    assert rejected.status_code == 401  # account has no MFA
    access = create_access_token(user.id)
    as_challenge = client.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": access, "code": "123456"}
    )
    assert as_challenge.status_code == 401
    expired = create_access_token(user.id, timedelta(seconds=-1))
    assert (
        client.post(
            "/api/v1/auth/mfa/verify", json={"mfa_token": expired, "code": "123456"}
        ).status_code
        == 401
    )
    assert body["user"]["mfa_enabled"] is False


def test_disable_needs_password_and_code_and_regeneration_replaces_codes(
    client: TestClient,
) -> None:
    body, _ = register(client)
    token = str(body["access_token"])
    secret, codes = enable_mfa(client, token)

    regenerated = client.post(
        "/api/v1/auth/mfa/recovery-codes",
        headers=bearer(token),
        json={"code": current_code(secret, 1)},
    )
    assert regenerated.status_code == 200
    new_codes = regenerated.json()["recovery_codes"]
    assert set(new_codes).isdisjoint(codes)

    wrong_password = client.post(
        "/api/v1/auth/mfa/disable",
        headers=bearer(token),
        json={"password": "notThePassword1", "code": new_codes[0]},
    )
    assert wrong_password.status_code == 400
    assert wrong_password.json()["detail"] == "Current password is incorrect"
    old_code = client.post(
        "/api/v1/auth/mfa/disable",
        headers=bearer(token),
        json={"password": REGISTER_PAYLOAD["password"], "code": codes[0]},
    )
    assert old_code.status_code == 400

    disabled = client.post(
        "/api/v1/auth/mfa/disable",
        headers=bearer(token),
        json={"password": REGISTER_PAYLOAD["password"], "code": new_codes[1]},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    plain_login = client.post("/api/v1/auth/login", json=LOGIN)
    assert "access_token" in plain_login.json()
