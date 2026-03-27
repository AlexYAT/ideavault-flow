"""Project picker labels, callback payloads, and interaction with ``set_current_project``."""

from app.repositories import items_repo, sessions_repo
from app.services import project_picker_service, project_service


def test_button_label_marks_current() -> None:
    cur = project_picker_service.button_label("alpha", is_current=True)
    assert cur.startswith("• ")
    assert project_picker_service.button_label("alpha", is_current=False) == "alpha"


def test_callback_data_within_telegram_limit() -> None:
    name = "very-long-project-name-" * 5
    data = project_picker_service.callback_data_for_project(name)
    assert data.startswith(project_picker_service.CALLBACK_PREFIX)
    assert len(data.encode("utf-8")) <= 64


def test_resolve_roundtrip_after_item_exists(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="note",
        project="beta",
        status="new",
        priority="normal",
        source="api",
    )
    cb = project_picker_service.callback_data_for_project("beta")
    assert project_picker_service.resolve_project_from_callback(db_session, cb) == "beta"


def test_picker_lines_no_projects() -> None:
    t = project_picker_service.picker_message_lines(None, has_projects=False)
    assert "📂" in t
    assert "не выбран" in t
    assert "/set" in t


def test_select_other_project_triggers_reset(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="a",
        project="p1",
        status="new",
        priority="normal",
        source="api",
    )
    items_repo.create_item(
        db_session,
        text="b",
        project="p2",
        status="new",
        priority="normal",
        source="api",
    )
    assert project_service.set_current_project(db_session, "u", "p1") is True
    row = sessions_repo.get_session(db_session, "u")
    first_tid = row.active_chat_thread_id
    assert project_service.set_current_project(db_session, "u", "p2") is True
    row2 = sessions_repo.get_session(db_session, "u")
    assert row2.active_chat_thread_id != first_tid


def test_select_same_project_no_reset(db_session) -> None:
    items_repo.create_item(
        db_session,
        text="a",
        project="same",
        status="new",
        priority="normal",
        source="api",
    )
    assert project_service.set_current_project(db_session, "u", "same") is True
    tid = sessions_repo.get_session(db_session, "u").active_chat_thread_id
    assert project_service.set_current_project(db_session, "u", "same") is False
    assert sessions_repo.get_session(db_session, "u").active_chat_thread_id == tid
