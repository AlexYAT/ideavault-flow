"""Project context: resolve current_project and listing."""

from sqlalchemy.orm import Session

from app.repositories import items_repo, sessions_repo
from app.services import chat_history_service


def set_current_project(db: Session, user_id: str, name: str | None) -> bool:
    """
    Set ``current_project`` for ``user_id`` (creates session row if needed).

    Returns:
        ``True`` if the effective project scope changed and a new chat thread was opened.
    """
    old = get_current_project(db, user_id)
    if old == name:
        sessions_repo.upsert_current_project(db, user_id, name)
        return False
    sessions_repo.upsert_current_project(db, user_id, name)
    chat_history_service.start_fresh_thread(db, user_id)
    return True


def clear_current_project(db: Session, user_id: str) -> bool:
    """
    Clear active project (set to ``NULL``) and refresh ``updated_at``.

    Returns:
        ``True`` if a project was cleared (scope changed) and a new chat thread was opened.
    """
    old = get_current_project(db, user_id)
    sessions_repo.upsert_current_project(db, user_id, None)
    if old is None:
        return False
    chat_history_service.start_fresh_thread(db, user_id)
    return True


def get_current_project(db: Session, user_id: str) -> str | None:
    """Return active project or ``None``."""
    row = sessions_repo.get_session(db, user_id)
    return row.current_project if row else None


def list_distinct_projects(db: Session) -> list[str]:
    """Distinct project names from items (non-null), sorted by name."""
    return items_repo.list_distinct_project_names(db)


def get_chat_mode(db: Session, user_id: str) -> str:
    """Return ``vault`` (default search/capture) or ``rag`` (knowledge base Q&A)."""
    row = sessions_repo.get_session(db, user_id)
    if row is None or not row.chat_mode:
        return "vault"
    return row.chat_mode if row.chat_mode in ("vault", "rag") else "vault"


def set_chat_mode(db: Session, user_id: str, mode: str) -> bool:
    """
    Persist bot mode; unknown values normalized to ``vault``.

    Returns:
        ``True`` if mode changed and a new chat thread was opened.
    """
    old = get_chat_mode(db, user_id)
    normalized = mode if mode in ("vault", "rag") else "vault"
    if old == normalized:
        sessions_repo.upsert_chat_mode(db, user_id, normalized)
        return False
    sessions_repo.upsert_chat_mode(db, user_id, normalized)
    chat_history_service.start_fresh_thread(db, user_id)
    return True
