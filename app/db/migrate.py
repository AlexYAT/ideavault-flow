"""Lightweight SQLite column adds (until Alembic)."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.project_constants import SYSTEM_NULL_DESCRIPTION_DEFAULT, SYSTEM_NULL_PROJECT_NAME


def apply_sqlite_migrations(engine: Engine) -> None:
    """Add columns introduced after first deploy."""
    if not str(engine.url).startswith("sqlite"):
        return
    insp = inspect(engine)
    if not insp.has_table("sessions"):
        return
    existing = {c["name"] for c in insp.get_columns("sessions")}
    with engine.begin() as conn:
        if "chat_mode" not in existing:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN chat_mode VARCHAR(32) DEFAULT 'vault'"))
        if "active_chat_thread_id" not in existing:
            conn.execute(text("ALTER TABLE sessions ADD COLUMN active_chat_thread_id INTEGER"))

    insp = inspect(engine)
    with engine.begin() as conn:
        if not insp.has_table("project_registry"):
            conn.execute(
                text(
                    """
                    CREATE TABLE project_registry (
                        name VARCHAR(255) PRIMARY KEY,
                        description TEXT NOT NULL DEFAULT '',
                        is_system INTEGER NOT NULL DEFAULT 0
                    )
                    """
                ),
            )
            conn.execute(
                text(
                    "INSERT INTO project_registry (name, description, is_system) "
                    "VALUES (:n, :d, 1)",
                ),
                {
                    "n": SYSTEM_NULL_PROJECT_NAME,
                    "d": SYSTEM_NULL_DESCRIPTION_DEFAULT,
                },
            )
        else:
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO project_registry (name, description, is_system) "
                    "VALUES (:n, :d, 1)",
                ),
                {
                    "n": SYSTEM_NULL_PROJECT_NAME,
                    "d": SYSTEM_NULL_DESCRIPTION_DEFAULT,
                },
            )
