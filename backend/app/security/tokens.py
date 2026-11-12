import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

from jose import JWTError, jwt

from app.core.config import settings
from app.security.crypto import utcnow

ALGORITHM = "HS256"


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user_id: str, session_id: str, role: str, org_id: str | None) -> tuple[str, int]:
    now = utcnow()
    expires = now + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "role": role,
        "org": org_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": uuid4().hex,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, int((expires - now).total_seconds())


def create_refresh_token() -> tuple[str, str, int]:
    token = secrets.token_urlsafe(48)
    expires_seconds = settings.refresh_token_days * 24 * 3600
    return token, hash_refresh_token(token), expires_seconds


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise ValueError("Invalid token type")
    return payload


def create_reset_token(user_id: str) -> str:
    now = utcnow()
    payload = {
        "sub": user_id,
        "type": "reset",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.reset_token_minutes)).timestamp()),
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_reset_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired reset token") from exc
    if payload.get("type") != "reset":
        raise ValueError("Invalid token type")
    return payload
