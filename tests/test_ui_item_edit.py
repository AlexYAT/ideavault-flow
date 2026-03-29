"""Web UI: редактирование текста заметки."""

from urllib.parse import quote, unquote

from fastapi.testclient import TestClient


def test_ui_item_edit_page_shows_text_and_ref(client: TestClient) -> None:
    r = client.post(
        "/api/items",
        json={
            "text": "orig",
            "project": "EditP",
            "source": "api",
            "raw_payload_ref": "data/x/y.bin",
        },
    )
    assert r.status_code == 200
    iid = r.json()["id"]

    page = client.get(f"/ui/items/{iid}/edit", params={"return_project": "EditP"})
    assert page.status_code == 200
    assert "orig" in page.text
    assert "Файл не найден" in page.text
    assert "<code>api</code>" in page.text


def test_ui_item_edit_post_updates_and_redirects(client: TestClient) -> None:
    c = client.post(
        "/api/items",
        json={"text": "old", "project": None, "source": "api"},
    )
    assert c.status_code == 200
    iid = c.json()["id"]

    resp = client.post(
        f"/ui/items/{iid}/edit",
        data={"text": "new body", "return_project": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    loc = resp.headers.get("location") or ""
    assert "/ui/items" in loc
    assert "msg=" in loc
    msg_val = unquote(loc.split("msg=", 1)[-1])
    assert "обновлена" in msg_val.lower() or "Заметка" in msg_val

    listed = client.get("/api/items", params={"limit": 50}).json()
    row = next(x for x in listed if x["id"] == iid)
    assert row["text"] == "new body"


def test_ui_item_edit_with_return_project_filter(client: TestClient) -> None:
    c = client.post(
        "/api/items",
        json={"text": "z", "project": "RProj", "source": "api"},
    )
    assert c.status_code == 200
    iid = c.json()["id"]

    qp = quote("RProj", safe="")
    r = client.post(
        f"/ui/items/{iid}/edit",
        data={"text": "updated z", "return_project": "RProj"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    loc = r.headers.get("location") or ""
    assert f"project={qp}" in loc


def test_ui_items_list_has_edit_link(client: TestClient) -> None:
    c = client.post(
        "/api/items",
        json={"text": "row", "project": "LinkP", "source": "api"},
    )
    assert c.status_code == 200
    iid = c.json()["id"]

    qp = quote("LinkP", safe="")
    page = client.get("/ui/items", params={"project": "LinkP"})
    assert page.status_code == 200
    assert f"/ui/items/{iid}/edit" in page.text
    assert "Редактировать" in page.text
