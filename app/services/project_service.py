"""Project context: resolve current_project and listing."""

from sqlalchemy.orm import Session

from app.repositories import items_repo, sessions_repo


def set_current_project(db: Session, user_id: str, name: str | None) -> None:
    """Telegram /set and /clear semantics. TODO: validate project names."""
    sessions_repo.upsert_current_project(db, user_id, name)


def get_current_project(db: Session, user_id: str) -> str | None:
    """Return active project or None."""
    row = sessions_repo.get_session(db, user_id)
    return row.current_project if row else None


def list_distinct_projects(db: Session) -> list[str]:
    """Distinct project names from items (non-null), sorted by name."""
    return items_repo.list_distinct_project_names(db)
