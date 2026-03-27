"""Service-level tests for /review and /next (deterministic heuristics)."""

from app.repositories import items_repo
from app.services import next_actions_service, project_snapshot_service


def test_review_scoped_to_project(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="alpha note for scope",
        project="course-a",
        status="new",
        priority="normal",
        source="api",
    )
    items_repo.create_item(
        db_session,
        text="beta other project",
        project="course-b",
        status="new",
        priority="normal",
        source="api",
    )
    text = project_snapshot_service.format_project_review(db_session, current_project="course-a")
    assert "course-a" in text
    assert "alpha note" in text
    assert "beta other" not in text


def test_review_global_scope(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="global one",
        project="p1",
        status="new",
        priority="normal",
        source="api",
    )
    items_repo.create_item(
        db_session,
        text="global two",
        project=None,
        status="new",
        priority="normal",
        source="api",
    )
    text = project_snapshot_service.format_project_review(db_session, current_project=None)
    assert "все заметки" in text.lower() or "не задан" in text
    assert "global one" in text
    assert "global two" in text


def test_next_returns_actions_when_notes_exist(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="идея для MVP и пользователи",
        project="x",
        status="new",
        priority="normal",
        source="telegram",
    )
    steps = next_actions_service.suggest_next_actions(db_session, current_project="x")
    assert 3 <= len(steps) <= 5
    joined = " ".join(steps).lower()
    assert "mvp" in joined or "иде" in joined or "пользовател" in joined or "сценари" in joined


def test_next_sparse_empty_vault(db_session) -> None:
    steps = next_actions_service.suggest_next_actions(db_session, current_project=None)
    assert len(steps) >= 2
    low = " ".join(s.lower() for s in steps)
    assert "добавьте" in low or "+" in low
