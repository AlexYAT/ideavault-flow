"""`/ui/rag`: project query, GitHub path validation (mocked)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.rag_binding_service import GithubPathsValidationResult, format_bind_result_message, validate_github_paths


def test_validate_github_paths_partitions() -> None:
    def probe(_r: str, _b: str, path: str) -> bool:
        return path == "ok.md"

    r = validate_github_paths("o/r", "main", ["ok.md", "bad.zzz"], probe=probe)
    assert r is not None
    assert r.valid == ["ok.md"]
    assert r.invalid == ["bad.zzz"]


def test_format_mixed_message() -> None:
    msg = format_bind_result_message(
        "demo",
        GithubPathsValidationResult(valid=["a.md"], invalid=["x.y"]),
    )
    assert "demo" in msg
    assert "1" in msg
    assert "x.y" in msg
    assert "Не найдены:" in msg


def test_ui_rag_get_shows_binding_for_project(client: TestClient) -> None:
    def fake_val(*_a, **_k):
        return GithubPathsValidationResult(valid=["README.md"], invalid=[])

    with patch("app.api.routes.ui.validate_github_paths", fake_val):
        assert client.post("/api/items", json={"text": "n", "project": "projA", "source": "api"}).status_code == 200
        assert client.post("/api/items", json={"text": "n", "project": "projB", "source": "api"}).status_code == 200
        client.post(
            "/ui/rag/bind",
            data={
                "project": "projA",
                "repo": "owner/demo-a",
                "branch": "main",
                "files": "README.md",
            },
            follow_redirects=False,
        )
        client.post(
            "/ui/rag/bind",
            data={
                "project": "projB",
                "repo": "owner/demo-b",
                "branch": "dev",
                "files": "README.md",
            },
            follow_redirects=False,
        )
    ra = client.get("/ui/rag?project=projA")
    assert ra.status_code == 200
    assert "owner/demo-a" in ra.text
    rb = client.get("/ui/rag?project=projB")
    assert rb.status_code == 200
    assert "owner/demo-b" in rb.text
    assert "dev" in rb.text


def test_ui_rag_mixed_paths_saves_only_valid(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.ui.validate_github_paths",
        lambda *a, **k: GithubPathsValidationResult(valid=["good.md"], invalid=["bad.txt"]),
    )
    client.post("/api/items", json={"text": "x", "project": "pmix", "source": "api"})
    r = client.post(
        "/ui/rag/bind",
        data={
            "project": "pmix",
            "repo": "o/r",
            "branch": "main",
            "files": "good.md\nbad.txt",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    loc = r.headers.get("location", "")
    assert "msg=" in loc
    assert "pmix" in loc
    r2 = client.get(loc)
    assert r2.status_code == 200
    assert "Не найдены:" in r2.text
    assert "bad.txt" in r2.text
    assert "1" in r2.text


def test_ui_rag_all_invalid_does_not_overwrite_binding(client: TestClient, monkeypatch) -> None:
    client.post("/api/items", json={"text": "x", "project": "pinv", "source": "api"})

    monkeypatch.setattr(
        "app.api.routes.ui.validate_github_paths",
        lambda *a, **k: GithubPathsValidationResult(valid=["keep.md"], invalid=[]),
    )
    client.post(
        "/ui/rag/bind",
        data={"project": "pinv", "repo": "a/b", "branch": "main", "files": "keep.md"},
        follow_redirects=False,
    )

    monkeypatch.setattr(
        "app.api.routes.ui.validate_github_paths",
        lambda *a, **k: GithubPathsValidationResult(valid=[], invalid=["nope.md"]),
    )
    client.post(
        "/ui/rag/bind",
        data={"project": "pinv", "repo": "x/y", "branch": "main", "files": "nope.md"},
        follow_redirects=False,
    )
    page = client.get("/ui/rag?project=pinv")
    assert page.status_code == 200
    assert "a/b" in page.text
    assert "keep.md" in page.text
