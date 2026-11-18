"""Tests for /predict, /predictions and /predictions/{id}/image."""

from pathlib import Path

import pytest

from tests.helpers import image_bytes, register_and_login

DATASET_TEST = Path(__file__).resolve().parents[2] / "training" / "dataset" / "test"


def upload(client, headers, data: bytes, name="photo.png", mime="image/png"):
    return client.post("/predict", headers=headers, files={"file": (name, data, mime)})


def test_predict_requires_login(client):
    assert upload(client, {}, image_bytes()).status_code == 401


@pytest.mark.parametrize("fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")])
def test_predict_accepts_formats_and_returns_probabilities(client, fmt, mime):
    headers = register_and_login(client)
    r = upload(client, headers, image_bytes(fmt), f"x.{fmt.lower()}", mime)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["predicted_label"] in {"cat", "dog", "other"}
    assert set(body["probabilities"]) == {"cat", "dog", "other"}
    assert abs(sum(body["probabilities"].values()) - 1) < 1e-3
    assert 0 <= body["confidence"] <= 1
    assert body["model_version"] == "1.0.0"
    assert isinstance(body["low_confidence"], bool)


@pytest.mark.parametrize("label", ["cat", "dog", "other"])
def test_predict_real_test_images(client, label):
    """End-to-end with real held-out photos: the model should get most of them right."""
    files = sorted((DATASET_TEST / label).glob("*.jpg"))[:5]
    if not files:
        pytest.skip("dataset not prepared")
    headers = register_and_login(client)
    labels = [upload(client, headers, f.read_bytes(), f.name, "image/jpeg").json()["predicted_label"]
              for f in files]
    assert labels.count(label) >= 4, labels


def test_rejects_non_image(client):
    headers = register_and_login(client)
    r = upload(client, headers, b"hello, I am a text file", "notes.png", "image/png")
    assert r.status_code == 400


def test_rejects_unsupported_format(client):
    headers = register_and_login(client)
    r = upload(client, headers, image_bytes("GIF"), "anim.gif", "image/gif")
    assert r.status_code == 415


def test_rejects_corrupted_image(client):
    headers = register_and_login(client)
    data = image_bytes("JPEG", size=(800, 600))
    r = upload(client, headers, data[: len(data) // 2], "broken.jpg", "image/jpeg")  # truncated
    assert r.status_code == 400


def test_rejects_file_over_5mb(client):
    headers = register_and_login(client)
    r = upload(client, headers, b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024), "big.jpg", "image/jpeg")
    assert r.status_code == 413


def test_history_pagination_and_privacy(client):
    alice = register_and_login(client, "alice@example.com")
    for _ in range(3):
        assert upload(client, alice, image_bytes()).status_code == 200

    page1 = client.get("/predictions?page=1&page_size=2", headers=alice).json()
    page2 = client.get("/predictions?page=2&page_size=2", headers=alice).json()
    assert page1["total"] == 3 and page1["pages"] == 2
    assert len(page1["items"]) == 2 and len(page2["items"]) == 1
    ids = {i["id"] for i in page1["items"]} | {i["id"] for i in page2["items"]}
    assert len(ids) == 3

    bob = register_and_login(client, "bob@example.com")
    assert client.get("/predictions", headers=bob).json()["total"] == 0


def test_history_requires_login_and_validates_params(client):
    assert client.get("/predictions").status_code == 401
    headers = register_and_login(client)
    assert client.get("/predictions?page=0", headers=headers).status_code == 422
    assert client.get("/predictions?page_size=1000", headers=headers).status_code == 422


def test_image_only_visible_to_owner(client):
    alice = register_and_login(client, "alice@example.com")
    url = upload(client, alice, image_bytes()).json()["image_url"]

    r = client.get(url, headers=alice)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"

    bob = register_and_login(client, "bob@example.com")
    assert client.get(url, headers=bob).status_code == 404
