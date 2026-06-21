import base64
import hashlib
from typing import Optional

from config.settings import get_settings

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - allows dev installs without cryptography.
    Fernet = None


def _fernet() -> Optional["Fernet"]:
    key = get_settings().token_encryption_key
    if not key or Fernet is None:
        return None
    try:
        return Fernet(key.encode())
    except Exception:
        digest = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    fernet = _fernet()
    if not fernet:
        return value
    return fernet.encrypt(value.encode()).decode()


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    fernet = _fernet()
    if not fernet:
        return value
    try:
        return fernet.decrypt(value.encode()).decode()
    except Exception:
        return value
