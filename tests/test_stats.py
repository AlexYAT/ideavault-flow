"""GET /stats vault aggregates."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("path", ["/stats", "/api/stats"])
def test_vault_stats(path: str, client: TestClient) -> None:
    client.post("/api/items", json={"text": "a", "project": "p1"})
    client.post("/api/items", json={"text": "b", "project": "p2"})
    client.post("/api/items", json={"text": "c", "project": None})
    res = client.get(path)
    assert res.status_code == 200
    body = res.json()
    assert body["items_total"] == 3
    assert body["projects_total"] == 2
    assert body["items_with_project"] == 2
    assert body["rag_documents_total"] == 0
    assert body["rag_chunks_total"] == 0
    assert body["rag_projects_with_docs"] == 0
