"""
Database connection.

engine        - the connection pool to PostgreSQL
SessionLocal  - factory that creates a database session (one per request)
Base          - parent class for all table classes (models)
get_db        - FastAPI dependency: opens a session, closes it after the request
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
