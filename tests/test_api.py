"""HTTP API smoke tests against an isolated in-memory database."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    for path in ("/api/health", "/health"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_create_and_list_items(client: TestClient) -> None:
    create = client.post(
        "/api/items",
        json={"text": "hello world note", "project": "demo", "source": "api"},
    )
    assert create.status_code == 200
    data = create.json()
    assert data["text"] == "hello world note"
    assert data["project"] == "demo"
    assert data["status"] == "new"
    assert data["source"] == "api"
    assert "id" in data

    listed = client.get("/api/items", params={"limit": 10})
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["text"] == "hello world note"
    assert rows[0]["created_at"]


def test_search_hits(client: TestClient) -> None:
    client.post("/api/items", json={"text": "alpha uniquetoken beta", "project": "p1"})
    for search_path in ("/api/search", "/search"):
        res = client.get(search_path, params={"q": "uniquetoken"})
        assert res.status_code == 200
        body = res.json()
        assert body["query"] == "uniquetoken"
        assert "items" in body
        assert len(body["items"]) >= 1
        assert body["items"][0]["text"] == "alpha uniquetoken beta"


def test_projects_distinct_sorted(client: TestClient) -> None:
    client.post("/api/items", json={"text": "a", "project": "zebra"})
    client.post("/api/items", json={"text": "b", "project": "alpha"})
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert res.json() == ["alpha", "zebra"]


def test_review_stub_no_hits(client: TestClient) -> None:
    res = client.post(
        "/api/review/ask",
        json={"user_id": "1", "message": "somethingonlynotinderby fts"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "ничего не нашлось" in body["answer"].lower()
    assert body["sources"] == []
    assert len(body["next_steps"]) >= 2


def test_review_stub_with_hits(client: TestClient) -> None:
    client.post("/api/items", json={"text": "vault secret phrase xyzzy", "project": "demo"})
    res = client.post(
        "/api/review/ask",
        json={"user_id": "1", "message": "xyzzy"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["sources"]
    assert "Нашёл" in body["answer"] or "релевант" in body["answer"].lower()
    assert body["next_steps"]


def test_review_snapshot_get(client: TestClient) -> None:
    client.post("/api/items", json={"text": "line for snapshot", "project": "snap"})
    for review_path in ("/api/review", "/review"):
        res = client.get(review_path, params={"project": "snap"})
        assert res.status_code == 200
        body = res.json()
        assert body["project"] == "snap"
        assert "line for snapshot" in body["review"]
        assert "Фокус" in body["review"] or "фокус" in body["review"].lower()

    res_all = client.get("/review")
    assert res_all.status_code == 200
    assert res_all.json()["project"] is None
    assert len(res_all.json()["review"]) > 10
