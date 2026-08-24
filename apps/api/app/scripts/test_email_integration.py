import argparse
import os

from app.core.config import get_settings
from app.integrations.email.oauth import GmailOAuthClient
from app.integrations.email.policy import EmailPolicy
from app.integrations.email.providers.gmail import GmailProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Operator-gated Gmail integration smoke test")
    parser.add_argument("--allow-send", action="store_true")
    parser.add_argument("--recipient")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.email_integration_enabled:
        raise SystemExit("EMAIL_INTEGRATION_ENABLED must be true")
    refresh_token = os.environ.get("EMAIL_SMOKE_REFRESH_TOKEN")
    if not refresh_token:
        raise SystemExit("EMAIL_SMOKE_REFRESH_TOKEN is required at runtime")
    if args.allow_send and not args.recipient:
        raise SystemExit("--allow-send requires an explicit --recipient")
    if args.allow_send and not settings.email_send_enabled:
        raise SystemExit("EMAIL_SEND_ENABLED must be true for the explicit send smoke test")

    oauth = GmailOAuthClient(settings)
    access_token = oauth.refresh(refresh_token)
    policy = EmailPolicy(
        settings.email_allowed_account_list,
        max_recipients=settings.email_max_recipients,
        max_attachment_bytes=settings.email_max_attachment_bytes,
    )
    provider = GmailProvider(
        access_token,
        settings.email_api_timeout_seconds,
        max_body_chars=settings.email_max_body_chars,
        policy=policy,
    )
    try:
        profile = provider.profile()
        sender = policy.authorize_account(str(profile["emailAddress"]))
        page = provider.list_messages(1)
        print(f"read smoke passed for {sender}; messages={len(page.messages)}")
        if args.allow_send:
            result = provider.send(
                sender=sender,
                to=[args.recipient],
                cc=[],
                bcc=[],
                subject="Kiko email integration smoke test",
                body="Explicit operator-authorized smoke test.",
                idempotency_key="operator-smoke-test",
            )
            print(f"send smoke passed; message_id={result.message_id}")
    finally:
        provider.close()


if __name__ == "__main__":
    main()
