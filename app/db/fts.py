"""
SQLite FTS5 external-content index over `items.text`.

Virtual table `items_fts` stays in sync via triggers on `items`.
TODO: tune tokenizers, add project column to FTS if needed for ranking.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    text,
    content='items',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);
"""

_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
      INSERT INTO items_fts(rowid, text) VALUES (new.id, new.text);
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
      INSERT INTO items_fts(items_fts, rowid, text) VALUES ('delete', old.id, old.text);
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
      INSERT INTO items_fts(items_fts, rowid, text) VALUES ('delete', old.id, old.text);
      INSERT INTO items_fts(rowid, text) VALUES (new.id, new.text);
    END;
    """,
]


def ensure_fts(engine: Engine) -> None:
    """Create FTS virtual table and sync triggers if missing (SQLite only)."""
    if not str(engine.url).startswith("sqlite"):
        # TODO: Postgres/pgvector or other backends
        return
    with engine.begin() as conn:
        conn.execute(text(_FTS_DDL))
        for stmt in _TRIGGERS:
            conn.execute(text(stmt))
        # Backfill if table existed before FTS (idempotent for empty index)
        conn.execute(
            text(
                """
                INSERT INTO items_fts(rowid, text)
                SELECT id, text FROM items
                WHERE NOT EXISTS (SELECT 1 FROM items_fts WHERE items_fts.rowid = items.id)
                """
            )
        )
