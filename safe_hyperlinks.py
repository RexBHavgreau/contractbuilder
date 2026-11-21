"""Validation for the external hyperlink schemes supported by Contract Builder."""
from __future__ import annotations

from urllib.parse import unquote, urlsplit


_ALLOWED_SCHEMES = {"http", "https", "mailto"}


def safe_hyperlink_target(target: object) -> str | None:
    """Return a safe external URL, or None for malformed/unsupported targets.

    Web URLs must have a host and cannot contain user-info credentials.
    Mail links must identify at least one address. Whitespace, control
    characters, backslashes and markup delimiters are rejected in all URLs.
    """
    if not isinstance(target, str) or not target or target != target.strip():
        return None
    if any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        or character in '<>"\\|'
        for character in target
    ):
        return None
    try:
        decoded = unquote(target)
        if any(
            ord(character) < 32
            or ord(character) == 127
            or character in '<>"\\'
            for character in decoded
        ):
            return None
        parsed = urlsplit(target)
        scheme = parsed.scheme.lower()
        if scheme not in _ALLOWED_SCHEMES:
            return None
        if scheme in {"http", "https"}:
            if not parsed.netloc or not parsed.hostname:
                return None
            if parsed.username is not None or parsed.password is not None:
                return None
            # Accessing .port performs urllib's range and syntax validation.
            _ = parsed.port
            return target
        if parsed.netloc or not parsed.path:
            return None
        addresses = parsed.path.split(",")
        for address in addresses:
            if address.count("@") != 1:
                return None
            local, domain = address.rsplit("@", 1)
            if (
                not local
                or not domain
                or domain.startswith(".")
                or domain.endswith(".")
                or ".." in domain
                or any(character in local + domain for character in '<>()[]:;"/')
            ):
                return None
        return target
    except ValueError:
        return None
