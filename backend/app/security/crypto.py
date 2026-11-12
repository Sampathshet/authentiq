import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fernet() -> Fernet:
    digest = hashlib.sha256((settings.secret_key + ":authentiq-fernet-v1").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    try:
        return _fernet().decrypt(data)
    except InvalidToken as exc:
        raise ValueError("Encrypted payload could not be decrypted") from exc


def encrypt_text(value: str) -> str:
    return encrypt_bytes(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str) -> str:
    return decrypt_bytes(value.encode("ascii")).decode("utf-8")


def random_secret_hex(length: int = 32) -> str:
    return secrets.token_hex(length)


def random_url_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_hex(value.encode("utf-8"))


def constant_time_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def parse_expiry(expires_in_hours: int) -> datetime:
    return utcnow() + timedelta(hours=expires_in_hours)
