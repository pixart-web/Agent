import smtplib
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.transactional_email import TransactionalEmailOutbox
from app.security.account_tokens import decrypt_email_payload


class TransactionalEmailDispatcher:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def dispatch_batch(self) -> tuple[int, int]:
        if not self.settings.transactional_email_enabled:
            return (0, 0)
        sent = failed = 0
        for _ in range(self.settings.transactional_email_batch_size):
            item = self.session.scalar(
                select(TransactionalEmailOutbox)
                .where(
                    TransactionalEmailOutbox.status == "pending",
                    TransactionalEmailOutbox.available_at <= utc_now(),
                    TransactionalEmailOutbox.attempts
                    < self.settings.transactional_email_max_attempts,
                )
                .order_by(
                    TransactionalEmailOutbox.available_at,
                    TransactionalEmailOutbox.created_at,
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if item is None:
                break
            item.status = "sending"
            item.attempts += 1
            self.session.flush()
            try:
                self._send(item)
            except Exception as error:
                failed += 1
                item.status = (
                    "failed"
                    if item.attempts >= self.settings.transactional_email_max_attempts
                    else "pending"
                )
                item.last_error_code = type(error).__name__[:64]
                item.available_at = utc_now() + timedelta(minutes=min(2 ** (item.attempts - 1), 60))
            else:
                sent += 1
                item.status = "sent"
                item.sent_at = utc_now()
                item.last_error_code = None
            self.session.commit()
        return sent, failed

    def _send(self, item: TransactionalEmailOutbox) -> None:
        payload = decrypt_email_payload(item.encrypted_payload, self.settings.auth_secret_key)
        subject, text = self._render(item.template, payload)
        message = EmailMessage()
        message["From"] = self.settings.transactional_email_from
        message["To"] = item.recipient
        message["Subject"] = subject
        message.set_content(text)

        if not self.settings.smtp_host:
            raise RuntimeError("SMTP host is not configured")
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as client:
            if self.settings.smtp_starttls:
                client.starttls()
            if self.settings.smtp_username:
                password = (
                    self.settings.smtp_password.get_secret_value()
                    if self.settings.smtp_password
                    else ""
                )
                client.login(self.settings.smtp_username, password)
            client.send_message(message)

    def _render(self, template: str, payload: dict[str, str]) -> tuple[str, str]:
        token = payload["token"]
        full_name = payload.get("full_name", "there")
        base = self.settings.public_web_url.rstrip("/")
        if template == "email_verification":
            link = f"{base}/verify-email?{urlencode({'token': token})}"
            return (
                "Verify your Kiko email",
                f"Hello {full_name},\n\nVerify your email using this link:\n{link}\n\n"
                "If you did not create this account, you can ignore this message.",
            )
        if template == "password_reset":
            link = f"{base}/reset-password?{urlencode({'token': token})}"
            return (
                "Reset your Kiko password",
                f"Hello {full_name},\n\nReset your password using this link:\n{link}\n\n"
                "If you did not request this change, you can ignore this message.",
            )
        if template == "workspace_invitation":
            link = f"{base}/invite?{urlencode({'token': token})}"
            workspace_name = payload["workspace_name"]
            return (
                f"Join {workspace_name} on Kiko",
                f"Hello {full_name},\n\nYou were invited to join {workspace_name} on Kiko:\n"
                f"{link}\n\nIf you were not expecting this invitation, ignore this message.",
            )
        raise ValueError("Unsupported transactional email template")
