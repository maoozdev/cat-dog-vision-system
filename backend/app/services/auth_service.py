"""
Authentication logic: users and refresh sessions.

Refresh-token rotation: every time /auth/refresh is used, the old session is
revoked and a new one is created. If an already-revoked token is used again
(a sign it was stolen), ALL sessions of that user are revoked.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models import Session as UserSession
from app.models import User
from app.utils.security import (DUMMY_HASH, hash_password, hash_refresh_token,
                                new_refresh_token, verify_password)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    """Some databases (SQLite in tests) return naive datetimes; treat them as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ users
def get_user_by_email(db: DbSession, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: DbSession, email: str, password: str) -> User:
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: DbSession, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_HASH)  # same work -> same timing
        return None
    return user if verify_password(password, user.password_hash) else None


# --------------------------------------------------------------- sessions
def create_session(db: DbSession, user_id: uuid.UUID, user_agent: str | None,
                   ip: str | None) -> str:
    """Create a session row and return the RAW refresh token (only the cookie gets it)."""
    token = new_refresh_token()
    db.add(UserSession(
        user_id=user_id,
        refresh_token_hash=hash_refresh_token(token),
        expires_at=utcnow() + timedelta(days=get_settings().refresh_token_days),
        user_agent=(user_agent or "")[:512] or None,
        ip=ip,
    ))
    db.commit()
    return token


def rotate_session(db: DbSession, token: str, user_agent: str | None,
                   ip: str | None) -> tuple[User, str] | None:
    """Validate a refresh token; return (user, new_token) or None if invalid."""
    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == hash_refresh_token(token))
    )
    if session is None:
        return None
    if session.revoked_at is not None:
        # Token reuse detected -> revoke everything for this user.
        revoke_all_sessions(db, session.user_id)
        logger.warning("refresh token reuse detected",
                       extra={"user_id": str(session.user_id), "event": "token_reuse"})
        return None
    if as_utc(session.expires_at) <= utcnow():
        return None

    session.revoked_at = utcnow()
    db.commit()
    new_token = create_session(db, session.user_id, user_agent, ip)
    return session.user, new_token


def revoke_session(db: DbSession, token: str) -> None:
    session = db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == hash_refresh_token(token))
    )
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()


def revoke_all_sessions(db: DbSession, user_id: uuid.UUID) -> None:
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()
