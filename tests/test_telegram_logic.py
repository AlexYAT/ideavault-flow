"""Service-layer tests for Telegram-related flows (no python-telegram-bot)."""

from sqlalchemy import func, select

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
    r1 = capture_service.capture_from_text(
        db_session,
        raw_text="+note one",
        current_project=project_service.get_current_project(db_session, "1"),
        source=CaptureSource.TELEGRAM,
    )
    assert r1 is not None
    assert not r1.is_duplicate
    row = db_session.get(Item, r1.item_id)
    assert row is not None
    assert row.text == "note one"
    assert row.project == "p-alpha"
    assert row.source == "telegram"

    r2 = capture_service.capture_from_text(
        db_session,
        raw_text="+orphan",
        current_project=None,
        source=CaptureSource.TELEGRAM,
    )
    assert r2 is not None
    assert not r2.is_duplicate
    row2 = db_session.get(Item, r2.item_id)
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


def test_capture_duplicate_returns_same_id(db_session) -> None:
    """Identical normalized text + project yields existing row, no second insert."""
    r1 = capture_service.capture_from_text(
        db_session,
        raw_text="+  Hello   World  ",
        current_project="p1",
        source=CaptureSource.TELEGRAM,
    )
    assert r1 is not None and not r1.is_duplicate
    r2 = capture_service.capture_from_text(
        db_session,
        raw_text="+hello world",
        current_project="p1",
        source=CaptureSource.TELEGRAM,
    )
    assert r2 is not None and r2.is_duplicate
    assert r2.item_id == r1.item_id

    stmt = select(func.count()).select_from(Item).where(Item.project == "p1")
    assert db_session.scalar(stmt) == 1


def test_capture_same_text_different_project_allowed(db_session) -> None:
    a = capture_service.capture_from_text(
        db_session,
        raw_text="+dup text",
        current_project="A",
        source=CaptureSource.TELEGRAM,
    )
    b = capture_service.capture_from_text(
        db_session,
        raw_text="+dup text",
        current_project="B",
        source=CaptureSource.TELEGRAM,
    )
    assert a is not None and b is not None
    assert not a.is_duplicate and not b.is_duplicate
    assert a.item_id != b.item_id


def test_capture_slight_text_change_allowed(db_session) -> None:
    a = capture_service.capture_from_text(
        db_session,
        raw_text="+hello",
        current_project=None,
        source=CaptureSource.TELEGRAM,
    )
    b = capture_service.capture_from_text(
        db_session,
        raw_text="+hello!",
        current_project=None,
        source=CaptureSource.TELEGRAM,
    )
    assert a is not None and b is not None
    assert a.item_id != b.item_id
    assert not b.is_duplicate


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
    assert "Нашёл" in out or "релевант" in out.lower()
    assert "•" in out
    assert "unique_seed_token" in out or "MVP" in out
