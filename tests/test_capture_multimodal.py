"""Multipart POST /api/capture (MVP multimodal)."""

import base64

from fastapi.testclient import TestClient

_MIN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
)


def test_capture_multimodal_success(client: TestClient) -> None:
    files = {"file": ("one.png", _MIN_PNG, "image/png")}
    data = {"caption": "idea sketch", "project": "mvp"}
    res = client.post("/api/capture", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "saved"
    assert body["caption"] == "idea sketch"
    assert body["project"] == "mvp"
    assert body["item_id"] >= 1
    assert "idea sketch" in body["capture"]


def test_capture_requires_file_or_errors(client: TestClient) -> None:
    res = client.post("/api/capture", data={})
    assert res.status_code == 400
    res2 = client.post("/api/capture", data={"caption": "only text"})
    assert res2.status_code == 400


def test_capture_rejects_non_image(client: TestClient) -> None:
    files = {"file": ("bad.txt", b"not a real image", "text/plain")}
    res = client.post("/api/capture", files=files)
    assert res.status_code == 400
    detail = str(res.json().get("detail", "")).lower()
    assert "image" in detail or "jpeg" in detail or "png" in detail or "поддерж" in detail
