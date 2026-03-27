"""Project context: resolve current_project and listing."""

from sqlalchemy.orm import Session

from app.repositories import items_repo, sessions_repo


def set_current_project(db: Session, user_id: str, name: str | None) -> None:
    """Set ``current_project`` for ``user_id`` (creates session row if needed)."""
    sessions_repo.upsert_current_project(db, user_id, name)


def clear_current_project(db: Session, user_id: str) -> None:
    """Clear active project (set to ``NULL``) and refresh ``updated_at``."""
    sessions_repo.upsert_current_project(db, user_id, None)


def get_current_project(db: Session, user_id: str) -> str | None:
    """Return active project or ``None``."""
    row = sessions_repo.get_session(db, user_id)
    return row.current_project if row else None


def list_distinct_projects(db: Session) -> list[str]:
    """Distinct project names from items (non-null), sorted by name."""
    return items_repo.list_distinct_project_names(db)
