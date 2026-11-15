"""Network classification helpers for endpoints Kiko may call."""

import ipaddress
from urllib.parse import urlsplit

PRIVATE_SUFFIXES = (".internal", ".local", ".lan", ".home.arpa", ".localhost")


def is_private_endpoint(url: str) -> bool:
    """True when `url` targets loopback, a private/link-local address or a private name.

    Accepted names: ``localhost``, single-label hosts (container/service names such as
    ``ollama``) and private DNS suffixes. Public names and addresses are rejected, so a
    misconfiguration cannot send prompts and business data to an external AI service.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    host = parts.hostname.rstrip(".").lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host == "localhost" or "." not in host or host.endswith(PRIVATE_SUFFIXES)
    return address.is_loopback or address.is_private or address.is_link_local
