import base64
import hashlib
import json
import secrets

from cryptography.fernet import Fernet, InvalidToken


def generate_account_token() -> str:
    return secrets.token_urlsafe(48)


def hash_account_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _fernet(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_email_payload(payload: dict[str, str], secret: str) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet(secret).encrypt(serialized).decode("ascii")


def decrypt_email_payload(ciphertext: str, secret: str) -> dict[str, str]:
    try:
        value = json.loads(_fernet(secret).decrypt(ciphertext.encode("ascii")))
    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid transactional email payload") from error
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise ValueError("Invalid transactional email payload")
    return value
