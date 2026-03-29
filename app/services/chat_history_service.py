"""
Chat thread lifecycle for Telegram: one active thread per (user, project key, mode).

Starting a new thread does not delete old rows — only moves ``sessions.active_chat_thread_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.tables import ChatMessage, ChatThread, UserSession
from app.repositories import chat_history_repo, sessions_repo

PROJECT_KEY_GLOBAL = "__global__"


def project_key(current_project: str | None) -> str:
    """Stable DB key for session scope (``None`` → global bucket)."""
    return current_project if current_project else PROJECT_KEY_GLOBAL


def _session_mode(row: UserSession | None) -> str:
    if row is None or not row.chat_mode:
        return "vault"
    return row.chat_mode if row.chat_mode in ("vault", "rag") else "vault"


def start_fresh_thread(db: Session, user_id: str) -> ChatThread:
    """
    Open a new :class:`~app.db.tables.ChatThread` and point ``sessions.active_chat_thread_id`` at it.

    Caller should run after project/mode changes or /resetchat.
    """
    sess = sessions_repo.get_session(db, user_id)
    if sess is None:
        sessions_repo.upsert_current_project(db, user_id, None)
        sess = sessions_repo.get_session(db, user_id)
    assert sess is not None
    pk = project_key(sess.current_project)
    mode = _session_mode(sess)
    thread = ChatThread(user_id=user_id, project_key=pk, mode=mode)
    db.add(thread)
    db.flush()
    sess.active_chat_thread_id = thread.id
    sess.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(thread)
    return thread


def ensure_chat_thread(db: Session, user_id: str) -> ChatThread:
    """Return active thread if it matches current project+mode; otherwise start a fresh one."""
    sess = sessions_repo.get_session(db, user_id)
    if sess is None:
        sessions_repo.upsert_current_project(db, user_id, None)
        sess = sessions_repo.get_session(db, user_id)
    assert sess is not None
    pk = project_key(sess.current_project)
    mode = _session_mode(sess)
    tid = sess.active_chat_thread_id
    if tid is not None:
        existing = db.get(ChatThread, tid)
        if existing and existing.project_key == pk and existing.mode == mode:
            return existing
    return start_fresh_thread(db, user_id)


def list_active_thread_messages(db: Session, user_id: str, *, limit: int = 200) -> list[ChatMessage]:
    """
    Сообщения активного потока, если он согласован с текущим ``current_project`` и ``chat_mode`` сессии.

    Иначе пусто (например, после частичного обновления сессии без ``ensure_chat_thread``).
    """
    sess = sessions_repo.get_session(db, user_id)
    if sess is None or sess.active_chat_thread_id is None:
        return []
    t = db.get(ChatThread, sess.active_chat_thread_id)
    if t is None or t.user_id != user_id:
        return []
    pk = project_key(sess.current_project)
    if t.project_key != pk or t.mode != _session_mode(sess):
        return []
    return chat_history_repo.list_recent_messages_for_thread(db, t.id, limit=limit)
