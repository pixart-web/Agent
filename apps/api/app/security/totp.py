"""Time-based one-time passwords (RFC 6238, HMAC-SHA1, 30 s, 6 digits) and recovery codes.

Implemented with the standard library so authenticator apps (Google Authenticator, 1Password,
Microsoft Authenticator, Apple Passwords) work without an extra dependency.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from datetime import datetime
from urllib.parse import quote, urlencode

PERIOD_SECONDS = 30
DIGITS = 6
# Accept the previous and next 30 s step to absorb clock drift between the phone and server.
DRIFT_STEPS = 1
RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def generate_secret() -> str:
    """160-bit secret, base32 without padding (the format authenticator apps expect)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _key(secret: str) -> bytes:
    padded = secret.upper() + "=" * (-len(secret) % 8)
    return base64.b32decode(padded)


def time_step(now: datetime) -> int:
    return int(now.timestamp()) // PERIOD_SECONDS


def code_at(secret: str, step: int) -> str:
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def normalize_code(code: str) -> str:
    return "".join(character for character in code if not character.isspace())


def verify_code(secret: str, code: str, now: datetime, last_used_step: int | None) -> int | None:
    """Return the matched time step, or None. A step at or before `last_used_step` is refused,
    so an intercepted code cannot be replayed."""
    candidate = normalize_code(code)
    if len(candidate) != DIGITS or not candidate.isdigit():
        return None
    current = time_step(now)
    for step in range(current - DRIFT_STEPS, current + DRIFT_STEPS + 1):
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(code_at(secret, step), candidate):
            return step
    return None


def provisioning_uri(secret: str, account: str, issuer: str = "Kiko") -> str:
    label = quote(f"{issuer}:{account}")
    query = urlencode(
        {
            "secret": secret,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": DIGITS,
            "period": PERIOD_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{query}"


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    def one() -> str:
        characters = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        return f"{characters[:5]}-{characters[5:]}"

    return [one() for _ in range(count)]


def normalize_recovery_code(code: str) -> str:
    return "".join(character for character in code.lower() if character.isalnum())


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(normalize_recovery_code(code).encode("ascii", "ignore")).hexdigest()


def looks_like_recovery_code(code: str) -> bool:
    return len(normalize_recovery_code(code)) == 10
