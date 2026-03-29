"""Ссылки «назад в карточку проекта» с /ui/items и /ui/rag при явном project в query."""

from urllib.parse import quote

from fastapi.testclient import TestClient


def _mk_project(client: TestClient, name: str) -> None:
    r = client.post(
        "/ui/project/create",
        data={"name": name, "description": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_ui_items_shows_back_link_with_project_query(client: TestClient) -> None:
    _mk_project(client, "NavItems1")
    r = client.get("/ui/items", params={"project": "NavItems1"})
    assert r.status_code == 200
    assert "← К проекту NavItems1" in r.text
    q = quote("NavItems1", safe="")
    assert f'href="/ui/project/{q}"' in r.text
    assert "Показать все" in r.text


def test_ui_items_move_preserves_project_query(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        _mk_project(client, "KeepScope")
        _mk_project(client, "DstScope")
        c = client.post(
            "/api/items",
            json={"text": "move scope", "project": "KeepScope", "source": "api"},
        )
        assert c.status_code == 200
        iid = c.json()["id"]
        r = client.post(
            "/ui/items/move",
            data={
                "item_id": str(iid),
                "project": "DstScope",
                "return_project": "KeepScope",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
        loc = r.headers.get("location") or ""
        assert "project=KeepScope" in loc
    finally:
        monkeypatch.delenv("API_KEY", raising=False)
        get_settings.cache_clear()


def test_ui_items_select_has_no_null_option(client: TestClient) -> None:
    r = client.get("/ui/items")
    assert r.status_code == 200
    assert '<option value="Null"' not in r.text


def test_ui_items_no_back_link_without_project_query(client: TestClient) -> None:
    r = client.get("/ui/items")
    assert r.status_code == 200
    assert "← К проекту" not in r.text


def test_ui_rag_shows_back_link_with_project_query(client: TestClient) -> None:
    _mk_project(client, "NavRag1")
    r = client.get("/ui/rag", params={"project": "NavRag1"})
    assert r.status_code == 200
    assert "← К проекту NavRag1" in r.text
    q = quote("NavRag1", safe="")
    assert f'href="/ui/project/{q}"' in r.text


def test_ui_rag_no_back_link_without_project_query(client: TestClient) -> None:
    _mk_project(client, "NavRag2")
    r = client.get("/ui/rag")
    assert r.status_code == 200
    assert "← К проекту" not in r.text
