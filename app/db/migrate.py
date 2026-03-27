"""Lightweight SQLite column adds (until Alembic)."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


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
