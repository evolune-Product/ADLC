"""
Token encryption/decryption using Fernet symmetric encryption.

Key derivation note
--------------------
The padding byte here MUST be b"\\x00" (a null byte), not b"0" (the ASCII
digit). An earlier version of this module padded with b"0", which silently
derives a different key than intended — every token encrypted under that
version is unreadable by any correct implementation, and vice versa. If you
have ciphertext from that broken version, use `migrate_token()` below to
re-encrypt it under the correct key before anything else touches it.
"""
import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _load_fernet_key(raw_key: str) -> bytes:
    """
    Accept either a proper 44-char URL-safe base64 Fernet key, or an arbitrary
    string (e.g. a plain 32-char secret from .env) — truncated/padded to 32
    bytes with null bytes, then base64-encoded.
    """
    stripped = raw_key.strip()
    if len(stripped) == 44:
        try:
            decoded = base64.urlsafe_b64decode(stripped + "==")
            if len(decoded) == 32:
                return stripped.encode()
        except Exception:
            pass
    key_bytes = stripped.encode()[:32].ljust(32, b"\x00")
    return base64.urlsafe_b64encode(key_bytes)


@lru_cache(maxsize=1)
def _cached_fernet_key() -> bytes:
    return _load_fernet_key(settings.encryption_key)


def _fernet() -> Fernet:
    return Fernet(_cached_fernet_key())


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()


# ── Migration helper (one-time use) ──────────────────────────────────────────

def _old_broken_fernet(raw_key: str) -> Fernet:
    """Reproduces the OLD, broken derivation (pads with b"0") for migration only."""
    key_bytes = raw_key.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def migrate_token(encrypted: str, raw_key: str | None = None) -> str:
    """
    Decrypt a token that was encrypted with the OLD broken derivation, and
    re-encrypt it with the correct one. Run once per affected row:

        from app.services.encryption import migrate_token
        from app.database import SessionLocal
        from app.models.connection import Connection

        db = SessionLocal()
        for conn in db.query(Connection).filter(Connection.access_token.isnot(None)).all():
            try:
                conn.access_token = migrate_token(conn.access_token)
                if conn.refresh_token:
                    conn.refresh_token = migrate_token(conn.refresh_token)
            except InvalidToken:
                pass  # already on the correct key — nothing to migrate
        db.commit()
    """
    key = raw_key if raw_key is not None else settings.encryption_key
    plaintext = _old_broken_fernet(key).decrypt(encrypted.encode()).decode()
    return encrypt_token(plaintext)
