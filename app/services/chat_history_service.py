"""
Chat thread lifecycle for Telegram: one active thread per (user, project key, mode).

Starting a new thread does not delete old rows — only moves ``sessions.active_chat_thread_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.tables import ChatThread, UserSession
from app.repositories import sessions_repo

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
