"""
Passwords and tokens.

Password hashing - Argon2: slow on purpose, salted, so stolen hashes are hard to crack.
Access token     - short-lived JWT (signed JSON) sent in the Authorization header.
Refresh token    - long random string stored in an HttpOnly cookie; the DB keeps only
                   its SHA-256 hash.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# A real hash of a random password. Used to spend the same time on unknown e-mails,
# so attackers can't detect which e-mails are registered by measuring response time.
DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def create_access_token(user_id: uuid.UUID) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID | None:
    """Return the user id if the token is valid and not expired, else None."""
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)  # 384 random bits


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
