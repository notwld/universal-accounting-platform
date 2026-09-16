import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def hmac_email(email: str) -> str:
    key = settings.PII_HMAC_KEY.encode("utf-8")
    normalized = (email or "").strip().lower().encode("utf-8")
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()


def hash_for_audit(value: str | None) -> str | None:
    if not value:
        return None
    key = settings.PII_HMAC_KEY.encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


@lru_cache(maxsize=1)
def _fernet() -> Fernet | None:
    raw = settings.FIELD_ENCRYPTION_KEY
    if not raw:
        return None
    return Fernet(raw.encode("utf-8") if isinstance(raw, str) else raw)


def encrypt_field(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    f = _fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_field(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    f = _fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
