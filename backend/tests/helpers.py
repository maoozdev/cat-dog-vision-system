"""Small helper functions used by several test files."""

import io

from fastapi.testclient import TestClient
from PIL import Image

PASSWORD = "secret123"


def register_and_login(client: TestClient, email: str = "alice@example.com") -> dict:
    """Create a user, log in, return the Authorization header."""
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def image_bytes(fmt: str = "PNG", size=(320, 240), color=(120, 160, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return buf.getvalue()
