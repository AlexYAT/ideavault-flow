"""SQLAlchemy engine, session factory, and schema initialization."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import fts, rag_fts
from app.db.migrate import apply_sqlite_migrations
from app.db.tables import Base

def _sqlite_connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        # Allow use across threads (FastAPI + bot); fine for MVP SQLite.
        return {"check_same_thread": False}
    return {}


_engine_url = settings.database_url
if _engine_url.startswith("sqlite:///") and not _engine_url.startswith("sqlite:///:memory:"):
    Path(_engine_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args=_sqlite_connect_args(settings.database_url),
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def init_db() -> None:
    """
    Create application tables and FTS adjunct objects.

    TODO: migrate to Alembic when schema evolves.
    """
    Base.metadata.create_all(bind=engine)
    apply_sqlite_migrations(engine)
    fts.ensure_fts(engine)
    rag_fts.ensure_rag_fts(engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
