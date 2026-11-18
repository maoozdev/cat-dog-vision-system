"""Tests for /auth/* and /health."""

from tests.helpers import PASSWORD, register_and_login


def use_cookie(client, token: str) -> None:
    """Make the client send exactly this refresh token (replace whatever the server set)."""
    client.cookies.clear()
    client.cookies.set("refresh_token", token)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok" and body["model_loaded"] is True


def test_register_returns_user_without_password(client):
    r = client.post("/auth/register", json={"email": "Bob@Example.com", "password": PASSWORD})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "bob@example.com"  # stored lowercase
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": PASSWORD})
    r = client.post("/auth/register", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 409


def test_register_weak_password_and_bad_email(client):
    assert client.post("/auth/register", json={"email": "a@example.com", "password": "short1"}).status_code == 422
    assert client.post("/auth/register", json={"email": "a@example.com", "password": "lettersonly"}).status_code == 422
    assert client.post("/auth/register", json={"email": "not-an-email", "password": PASSWORD}).status_code == 422


def test_login_sets_httponly_cookie_and_me_works(client):
    client.post("/auth/register", json={"email": "c@example.com", "password": PASSWORD})
    r = client.post("/auth/login", json={"email": "c@example.com", "password": PASSWORD})
    assert r.status_code == 200
    cookie_header = r.headers["set-cookie"].lower()
    assert "refresh_token=" in cookie_header and "httponly" in cookie_header and "samesite=lax" in cookie_header

    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "c@example.com"


def test_login_wrong_password_and_unknown_user(client):
    client.post("/auth/register", json={"email": "d@example.com", "password": PASSWORD})
    assert client.post("/auth/login", json={"email": "d@example.com", "password": "wrong999"}).status_code == 401
    assert client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}).status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotates_token_and_detects_reuse(client):
    register_and_login(client)
    old = client.cookies.get("refresh_token")

    r = client.post("/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]
    new = client.cookies.get("refresh_token")
    assert new and new != old  # rotated

    # Re-using the OLD token (as a thief would) fails AND revokes all sessions.
    use_cookie(client, old)
    assert client.post("/auth/refresh").status_code == 401
    use_cookie(client, new)
    assert client.post("/auth/refresh").status_code == 401


def test_logout_revokes_refresh_session(client):
    register_and_login(client)
    token = client.cookies.get("refresh_token")
    assert client.post("/auth/logout").status_code == 204
    use_cookie(client, token)  # try to use it anyway
    assert client.post("/auth/refresh").status_code == 401


def test_refresh_without_cookie(client):
    assert client.post("/auth/refresh").status_code == 401


def test_login_rate_limit(client):
    codes = [client.post("/auth/login", json={"email": "x@example.com", "password": "nope1234"}).status_code
             for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
