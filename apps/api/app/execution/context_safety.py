import re
from collections.abc import Mapping, Sequence
from typing import Any

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "cookies",
    "refresh_token",
    "access_token",
    "secret",
    "credential",
    "credentials",
    "private_key",
}
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(" ", "_")
    return normalized in SENSITIVE_KEYS or any(
        marker in normalized for marker in ("password", "secret", "token", "api_key")
    )


def sanitize_execution_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _sensitive_key(str(key)) else sanitize_execution_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_execution_payload(item) for item in value]
    if isinstance(value, str):
        return BEARER_PATTERN.sub("Bearer [REDACTED]", value)
    return value
