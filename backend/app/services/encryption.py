import base64
from cryptography.fernet import Fernet
from app.config import settings


def _fernet() -> Fernet:
    # ENCRYPTION_KEY must be exactly 32 chars; encode to URL-safe base64 for Fernet
    key = settings.encryption_key.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()
