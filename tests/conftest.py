"""Pytest fixtures: isolated in-memory SQLite + dependency overrides."""

# Default: no live LLM in tests (user .env may enable it).
import os

os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("OPENAI_API_KEY", "")

try:
    from app.config import get_settings as _get_settings

    _get_settings.cache_clear()
except Exception:
    pass

from collections.abc import Generator
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import fts, rag_fts
from app.db.base import get_db
from app.db.migrate import apply_sqlite_migrations
from app.db.tables import Base
from app.main import app


@pytest.fixture(autouse=True)
def _tests_ignore_dotenv_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Перекрываем ``API_KEY`` из ``.env``: пустая строка в env сильнее, чем файл."""
    monkeypatch.setenv("API_KEY", "")
    try:
        from app.config import get_settings as _gs

        _gs.cache_clear()
    except Exception:
        pass


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Isolated in-memory DB session for service-layer tests (no HTTP)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    fts.ensure_fts(engine)
    rag_fts.ensure_rag_fts(engine)
    apply_sqlite_migrations(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient with ``get_db`` bound to a fresh in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    fts.ensure_fts(engine)
    rag_fts.ensure_rag_fts(engine)
    apply_sqlite_migrations(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Avoid touching the developer's on-disk SQLite during app lifespan startup.
    with mock.patch("app.main.init_db"):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()
