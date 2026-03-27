"""Service-layer tests for Telegram-related flows (no python-telegram-bot)."""

from app.core.enums import CaptureSource
from app.db.tables import Item
from app.repositories import items_repo, sessions_repo
from app.services import capture_service, chat_service, project_service


def test_session_row_created_on_set_project(db_session) -> None:
    """First ``set_current_project`` creates a ``sessions`` row."""
    assert sessions_repo.get_session(db_session, "99") is None
    project_service.set_current_project(db_session, "99", "alpha")
    row = sessions_repo.get_session(db_session, "99")
    assert row is not None
    assert row.current_project == "alpha"
    assert row.updated_at is not None


def test_get_clear_current_project(db_session) -> None:
    project_service.set_current_project(db_session, "7", "course")
    assert project_service.get_current_project(db_session, "7") == "course"
    project_service.clear_current_project(db_session, "7")
    assert project_service.get_current_project(db_session, "7") is None


def test_capture_with_project_and_global(db_session) -> None:
    project_service.set_current_project(db_session, "1", "p-alpha")
    i1 = capture_service.capture_from_text(
        db_session,
        raw_text="+note one",
        current_project=project_service.get_current_project(db_session, "1"),
        source=CaptureSource.TELEGRAM,
    )
    assert i1 is not None
    row = db_session.get(Item, i1)
    assert row is not None
    assert row.text == "note one"
    assert row.project == "p-alpha"
    assert row.source == "telegram"

    i2 = capture_service.capture_from_text(
        db_session,
        raw_text="+orphan",
        current_project=None,
        source=CaptureSource.TELEGRAM,
    )
    assert i2 is not None
    row2 = db_session.get(Item, i2)
    assert row2 is not None
    assert row2.project is None


def test_capture_empty_returns_none(db_session) -> None:
    assert (
        capture_service.capture_from_text(
            db_session,
            raw_text="+   ",
            current_project=None,
            source=CaptureSource.TELEGRAM,
        )
        is None
    )


def test_answer_text_query_uses_review_stub(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="unique_seed_token MVP idea",
        project="demo",
        status="new",
        priority="normal",
        source="api",
    )
    out = chat_service.answer_text_query(
        db_session,
        user_id="1",
        message="unique_seed_token",
        current_project=None,
    )
    assert "Найдено" in out
    assert "Источники:" in out
    assert "unique_seed_token" in out or "MVP" in out
