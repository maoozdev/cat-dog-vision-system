"""
Shared test setup (pytest "fixtures").

- Uses a temporary uploads folder.
- Uses an in-memory SQLite database instead of PostgreSQL, so tests are fast and
  never touch your real data. (Alembic + PostgreSQL are checked separately.)
- Loads the REAL trained model, so prediction tests are end-to-end.
"""

import os
import tempfile

# Must be set BEFORE the app is imported (settings are read at import time).
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="catdog-test-uploads-")
os.environ["COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register tables)
from app.database import Base, get_db
from app.main import app
from app.routers.auth import auth_limiter, refresh_limiter
from app.routers.predictions import predict_limiter


@pytest.fixture()
def client():
    # StaticPool = every session shares ONE in-memory database connection.
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    auth_limiter.reset()
    refresh_limiter.reset()
    predict_limiter.reset()
    with TestClient(app) as c:  # `with` runs startup -> model gets loaded
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
