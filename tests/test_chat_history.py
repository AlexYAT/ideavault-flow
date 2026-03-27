"""Chat thread lifecycle: scope by user + project + mode, reset on switch."""

from app.db.tables import ChatThread
from app.repositories import sessions_repo
from app.services import chat_history_service, project_service


def test_first_message_global_thread(db_session) -> None:
    """Ensure chat thread is created for a user without a prior session."""
    t = chat_history_service.ensure_chat_thread(db_session, "u1")
    assert isinstance(t, ChatThread)
    assert t.project_key == chat_history_service.PROJECT_KEY_GLOBAL
    assert t.mode == "vault"
    row = sessions_repo.get_session(db_session, "u1")
    assert row is not None
    assert row.active_chat_thread_id == t.id


def test_project_switch_opens_new_thread(db_session) -> None:
    project_service.set_current_project(db_session, "u2", "proj-a")
    row_a = sessions_repo.get_session(db_session, "u2")
    tid_a = row_a.active_chat_thread_id
    assert tid_a is not None
    t_a = db_session.get(ChatThread, tid_a)
    assert t_a is not None
    assert t_a.project_key == "proj-a"

    assert project_service.set_current_project(db_session, "u2", "proj-b") is True
    row_b = sessions_repo.get_session(db_session, "u2")
    assert row_b.active_chat_thread_id != tid_a
    t_b = db_session.get(ChatThread, row_b.active_chat_thread_id)
    assert t_b is not None
    assert t_b.project_key == "proj-b"


def test_resetchat_new_thread_same_project(db_session) -> None:
    project_service.set_current_project(db_session, "u3", "x")
    row1 = sessions_repo.get_session(db_session, "u3")
    first = row1.active_chat_thread_id
    chat_history_service.start_fresh_thread(db_session, "u3")
    row2 = sessions_repo.get_session(db_session, "u3")
    assert row2.active_chat_thread_id != first
    t = db_session.get(ChatThread, row2.active_chat_thread_id)
    assert t is not None
    assert t.project_key == "x"


def test_mode_switch_new_thread(db_session) -> None:
    project_service.set_current_project(db_session, "u4", "p")
    row = sessions_repo.get_session(db_session, "u4")
    tid_v = row.active_chat_thread_id
    assert project_service.set_chat_mode(db_session, "u4", "rag") is True
    row2 = sessions_repo.get_session(db_session, "u4")
    assert row2.active_chat_thread_id != tid_v
    t = db_session.get(ChatThread, row2.active_chat_thread_id)
    assert t.mode == "rag"


def test_same_project_no_extra_reset(db_session) -> None:
    project_service.set_current_project(db_session, "u5", "same")
    row = sessions_repo.get_session(db_session, "u5")
    tid = row.active_chat_thread_id
    assert project_service.set_current_project(db_session, "u5", "same") is False
    row2 = sessions_repo.get_session(db_session, "u5")
    assert row2.active_chat_thread_id == tid
