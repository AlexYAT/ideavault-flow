"""Sync SQLAlchemy session lifecycle for Telegram handlers (polling, short-lived)."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.db.base import SessionLocal


@contextmanager
def bot_session() -> Generator[Session, None, None]:
    """Yield a committed-on-success database session for one bot update."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
