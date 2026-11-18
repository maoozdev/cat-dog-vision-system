"""Production safety check: HTTPS mode must not run with a weak JWT secret."""

import pytest

from app.config import Settings


def test_production_refuses_default_secret():
    with pytest.raises(RuntimeError):
        Settings(cookie_secure=True, jwt_secret="dev-only-insecure-secret-change-me").check_production_safety()


def test_production_refuses_short_secret():
    with pytest.raises(RuntimeError):
        Settings(cookie_secure=True, jwt_secret="short").check_production_safety()


def test_production_accepts_strong_secret():
    Settings(cookie_secure=True, jwt_secret="x" * 48).check_production_safety()


def test_development_allows_default_secret():
    Settings(cookie_secure=False, jwt_secret="dev-only-insecure-secret-change-me").check_production_safety()
