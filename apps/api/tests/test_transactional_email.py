from email.message import EmailMessage

from app.core.config import Settings
from app.core.time import utc_now
from app.models.transactional_email import TransactionalEmailOutbox
from app.security.account_tokens import encrypt_email_payload
from app.services.transactional_email_service import TransactionalEmailDispatcher


class FakeSmtp:
    sent: list[EmailMessage] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        assert (host, port, timeout) == ("smtp.example.test", 587, 30)

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        assert (username, password) == ("mailer", "smtp-secret")

    def send_message(self, message: EmailMessage) -> None:
        self.sent.append(message)


class FailingSmtp(FakeSmtp):
    def send_message(self, message: EmailMessage) -> None:
        raise TimeoutError("provider unavailable")


def test_dispatches_encrypted_verification_email(db_session, monkeypatch) -> None:
    FakeSmtp.sent = []
    secret = "test-only-auth-secret-with-at-least-32-characters"
    item = TransactionalEmailOutbox(
        recipient="new-user@example.com",
        template="email_verification",
        encrypted_payload=encrypt_email_payload(
            {"token": "raw-secret-token", "full_name": "New User"}, secret
        ),
        available_at=utc_now(),
    )
    db_session.add(item)
    db_session.commit()
    monkeypatch.setattr("app.services.transactional_email_service.smtplib.SMTP", FakeSmtp)
    settings = Settings(
        app_env="test",
        auth_secret_key=secret,
        transactional_email_enabled=True,
        transactional_email_from="Kiko <no-reply@example.com>",
        smtp_host="smtp.example.test",
        smtp_username="mailer",
        smtp_password="smtp-secret",
        public_web_url="https://kiko.example.com",
    )

    assert TransactionalEmailDispatcher(db_session, settings).dispatch_batch() == (1, 0)
    db_session.refresh(item)
    assert item.status == "sent" and item.sent_at is not None
    assert len(FakeSmtp.sent) == 1
    body = FakeSmtp.sent[0].get_content()
    assert "https://kiko.example.com/verify-email?token=raw-secret-token" in body
    assert "raw-secret-token" not in item.encrypted_payload


def test_failed_delivery_is_retried_with_bounded_backoff(db_session, monkeypatch) -> None:
    secret = "test-only-auth-secret-with-at-least-32-characters"
    available_at = utc_now()
    item = TransactionalEmailOutbox(
        recipient="new-user@example.com",
        template="password_reset",
        encrypted_payload=encrypt_email_payload(
            {"token": "raw-secret-token", "full_name": "New User"}, secret
        ),
        available_at=available_at,
    )
    db_session.add(item)
    db_session.commit()
    monkeypatch.setattr("app.services.transactional_email_service.smtplib.SMTP", FailingSmtp)
    settings = Settings(
        app_env="test",
        auth_secret_key=secret,
        transactional_email_enabled=True,
        transactional_email_from="Kiko <no-reply@example.com>",
        smtp_host="smtp.example.test",
        smtp_username="mailer",
        smtp_password="smtp-secret",
        public_web_url="https://kiko.example.com",
        transactional_email_max_attempts=2,
    )

    assert TransactionalEmailDispatcher(db_session, settings).dispatch_batch() == (0, 1)
    db_session.refresh(item)
    assert item.status == "pending"
    assert item.attempts == 1
    assert item.last_error_code == "TimeoutError"
    assert item.available_at.replace(tzinfo=available_at.tzinfo) > available_at
