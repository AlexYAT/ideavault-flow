"""GET /ui/files — безопасная отдача файлов из data/."""

from pathlib import Path

from fastapi.testclient import TestClient


def _patch_data_roots(monkeypatch, tmp_path: Path):
    from app.api.routes import ui

    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ui, "PROJECT_ROOT", tmp_path.resolve())
    monkeypatch.setattr(ui, "DATA_ROOT", data.resolve())


def test_ui_files_returns_file_200(client: TestClient, tmp_path, monkeypatch) -> None:
    _patch_data_roots(monkeypatch, tmp_path)
    sub = tmp_path / "data" / "t"
    sub.mkdir()
    (sub / "hello.txt").write_text("hi", encoding="utf-8")

    r = client.get("/ui/files", params={"path": "data/t/hello.txt"})
    assert r.status_code == 200
    assert r.content == b"hi"


def test_ui_files_path_outside_data_403(client: TestClient, tmp_path, monkeypatch) -> None:
    _patch_data_roots(monkeypatch, tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    r = client.get("/ui/files", params={"path": "data/../outside.txt"})
    assert r.status_code == 403


def test_ui_files_not_found_404(client: TestClient, tmp_path, monkeypatch) -> None:
    _patch_data_roots(monkeypatch, tmp_path)
    (tmp_path / "data" / "only_dir").mkdir(parents=True)

    r = client.get("/ui/files", params={"path": "data/missing.bin"})
    assert r.status_code == 404


def test_ui_item_edit_has_open_file_link(client: TestClient, tmp_path, monkeypatch) -> None:
    _patch_data_roots(monkeypatch, tmp_path)
    pdir = tmp_path / "data" / "p"
    pdir.mkdir(parents=True)
    (pdir / "doc.bin").write_bytes(b"x")

    c = client.post(
        "/api/items",
        json={
            "text": "n",
            "project": "PX",
            "source": "api",
            "raw_payload_ref": "data/p/doc.bin",
        },
    )
    assert c.status_code == 200
    iid = c.json()["id"]

    page = client.get(f"/ui/items/{iid}/edit")
    assert page.status_code == 200
    assert "Открыть файл" in page.text
    assert "/ui/files?path=" in page.text
    assert "<img " not in page.text


def test_ui_item_edit_image_preview_telegram_photo(client: TestClient, tmp_path, monkeypatch) -> None:
    _patch_data_roots(monkeypatch, tmp_path)
    pdir = tmp_path / "data" / "tp"
    pdir.mkdir(parents=True)
    # минимальный валидный PNG 1×1
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (pdir / "shot.png").write_bytes(png)

    c = client.post(
        "/api/items",
        json={
            "text": "pic",
            "project": None,
            "source": "telegram_photo",
            "raw_payload_ref": "data/tp/shot.png",
        },
    )
    assert c.status_code == 200
    iid = c.json()["id"]

    page = client.get(f"/ui/items/{iid}/edit")
    assert page.status_code == 200
    assert "<img " in page.text
    assert "cursor:pointer" in page.text.replace(" ", "")


def test_ui_item_edit_image_preview_by_extension(client: TestClient, tmp_path, monkeypatch) -> None:
    _patch_data_roots(monkeypatch, tmp_path)
    pdir = tmp_path / "data" / "cap"
    pdir.mkdir(parents=True)
    (pdir / "a.webp").write_bytes(b"RIFF\x00\x00\x00\x00WEBP")

    c = client.post(
        "/api/items",
        json={
            "text": "w",
            "source": "api",
            "raw_payload_ref": "data/cap/a.webp",
        },
    )
    assert c.status_code == 200
    iid = c.json()["id"]

    page = client.get(f"/ui/items/{iid}/edit")
    assert page.status_code == 200
    assert "<img " in page.text
