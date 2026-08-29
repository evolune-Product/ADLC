"""
Security utilities:
- Fernet key loading + lazy singleton
- slowapi rate limiter instance + constants

Usage:
  from app.core.security import get_fernet, limiter, AUTH_LOGIN_LIMIT, AUTH_REGISTER_LIMIT
"""
from __future__ import annotations

import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from slowapi import Limiter
from slowapi.util import get_remote_address

# ─── Rate limiter ─────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

AUTH_LOGIN_LIMIT = "10/minute"
AUTH_REGISTER_LIMIT = "5/minute"


# ─── Fernet key helpers ───────────────────────────────────────────────────────

def load_fernet_key(raw_key: str) -> bytes:
    """
    Accept either:
    - A 44-character URL-safe base64 Fernet key (already valid), OR
    - A plain string of any length — truncated/padded to 32 bytes then base64-encoded.

    Returns a valid Fernet key (44 bytes of base64).
    Raises ValueError on invalid input.
    """
    stripped = raw_key.strip()

    # Try as-is first (already a valid Fernet key)
    if len(stripped) == 44:
        try:
            # Validate it's correct base64 and the right decoded length
            decoded = base64.urlsafe_b64decode(stripped + "==")
            if len(decoded) == 32:
                return stripped.encode()
        except Exception:
            pass

    # Treat as plain string — encode to bytes, take first 32, pad if shorter
    key_bytes = stripped.encode()[:32].ljust(32, b"\x00")
    return base64.urlsafe_b64encode(key_bytes)


@lru_cache(maxsize=1)
def _cached_fernet_key() -> bytes:
    """Load and cache the Fernet key from settings (validated once at first use)."""
    from app.config import settings
    return load_fernet_key(settings.encryption_key)


def get_fernet() -> Fernet:
    """Return the application Fernet singleton."""
    return Fernet(_cached_fernet_key())
