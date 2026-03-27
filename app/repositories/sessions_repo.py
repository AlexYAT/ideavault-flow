"""Persistence for per-user `UserSession` rows."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.tables import UserSession


def get_session(db: Session, user_id: str) -> UserSession | None:
    """Return session row or None."""
    return db.get(UserSession, user_id)


def upsert_current_project(db: Session, user_id: str, project: str | None) -> UserSession:
    """
    Set `current_project` for user, touching `updated_at`.

    TODO: merge with full session DTO, transaction boundaries with bot updates.
    """
    row = db.get(UserSession, user_id)
    now = datetime.now(timezone.utc)
    if row is None:
        row = UserSession(
            user_id=user_id,
            current_project=project,
            chat_mode="vault",
            updated_at=now,
        )
        db.add(row)
    else:
        row.current_project = project
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def upsert_chat_mode(db: Session, user_id: str, chat_mode: str) -> UserSession:
    """Set interaction mode (`vault` plain search vs `rag` knowledge base)."""
    row = db.get(UserSession, user_id)
    now = datetime.now(timezone.utc)
    if row is None:
        row = UserSession(
            user_id=user_id,
            current_project=None,
            chat_mode=chat_mode,
            updated_at=now,
        )
        db.add(row)
    else:
        row.chat_mode = chat_mode
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row
