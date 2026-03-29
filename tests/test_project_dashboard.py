"""Project dashboard: Null, delete → reassignment, CRUD flags."""

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.core.project_constants import SYSTEM_NULL_PROJECT_NAME
from app.repositories import project_registry_repo
from app.services import project_dashboard_service


def test_dashboard_lists_system_null(client: TestClient) -> None:
    r = client.get("/ui")
    assert r.status_code == 200
    assert SYSTEM_NULL_PROJECT_NAME in r.text
    assert "служебный" in r.text.lower() or "[служебный]" in r.text


def test_create_and_open_project(client: TestClient) -> None:
    c = client.post(
        "/ui/project/create",
        data={"name": "DashDemo", "description": "d1"},
        follow_redirects=True,
    )
    assert c.status_code == 200
    q = quote("DashDemo", safe="")
    r = client.get(f"/ui/project/{q}")
    assert r.status_code == 200
    assert "DashDemo" in r.text
    assert "d1" in r.text


def test_delete_moves_items_to_null_with_prefix(db_session) -> None:
    from app.repositories import items_repo

    project_registry_repo.create(db_session, name="gone", description="")
    items_repo.create_item(
        db_session,
        text="hello task",
        project="gone",
        status="new",
        priority="normal",
        source="test",
    )
    project_dashboard_service.delete_project_cascade(db_session, name="gone")
    rows = list(items_repo.list_items(db_session, project=SYSTEM_NULL_PROJECT_NAME, limit=50))
    assert len(rows) == 1
    assert SYSTEM_NULL_PROJECT_NAME == rows[0].project
    assert "Из удаленного gone" in rows[0].text
    assert "hello task" in rows[0].text


def test_delete_idempotent_prefix(db_session) -> None:
    from app.repositories import items_repo

    project_registry_repo.create(db_session, name="gone2", description="")
    items_repo.create_item(
        db_session,
        text="Из удаленного gone2\nalready",
        project="gone2",
        status="new",
        priority="normal",
        source="test",
    )
    project_dashboard_service.delete_project_cascade(db_session, name="gone2")
    rows = list(items_repo.list_items(db_session, project=SYSTEM_NULL_PROJECT_NAME, limit=50))
    assert rows[0].text.count("Из удаленного gone2") == 1


def test_cannot_delete_null_project(db_session) -> None:
    with pytest.raises(ValueError, match="Null"):
        project_dashboard_service.delete_project_cascade(db_session, name=SYSTEM_NULL_PROJECT_NAME)


def test_prefix_detection() -> None:
    assert project_dashboard_service.item_already_tagged_deleted_from("Из удаленного X\ny", "X")
    assert not project_dashboard_service.item_already_tagged_deleted_from("plain", "X")


def test_list_local_rag_files_relative_paths(tmp_path, monkeypatch) -> None:
    base = tmp_path / "ragroot"
    (base / "deep").mkdir(parents=True)
    (base / "top.txt").write_text("a", encoding="utf-8")
    (base / "deep" / "inner.md").write_text("b", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.project_dashboard_service.knowledge_dir",
        lambda _p: base,
    )
    files = project_dashboard_service.list_local_rag_files("AnyProject")
    assert sorted(files) == ["deep/inner.md", "top.txt"]


def test_list_local_rag_files_empty_when_missing(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(
        "app.services.project_dashboard_service.knowledge_dir",
        lambda _p: missing,
    )
    assert project_dashboard_service.list_local_rag_files("x") == []
