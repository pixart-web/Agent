"""Test helper: read the newest verification token queued for an address in a LOCAL test
database. Uses the API's own decryption; never run against staging or production."""

import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.transactional_email import TransactionalEmailOutbox
from app.security.account_tokens import decrypt_email_payload

settings = get_settings()
if "localhost" not in settings.database_url and "127.0.0.1" not in settings.database_url:
    raise SystemExit("refusing to read a non-local database")

with SessionLocal() as session:
    row = session.scalars(
        select(TransactionalEmailOutbox)
        .where(TransactionalEmailOutbox.recipient == sys.argv[1])
        .order_by(TransactionalEmailOutbox.created_at.desc())
    ).first()
    if row is None:
        raise SystemExit("no queued email")
    payload = decrypt_email_payload(row.encrypted_payload, settings.auth_secret_key)
    print(payload.get("token", ""))
