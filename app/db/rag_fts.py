"""SQLite FTS5 over ``rag_chunks.text`` (external content; swap to Chroma later via retriever interface)."""

from sqlalchemy import text
from sqlalchemy.engine import Engine

_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
    text,
    content='rag_chunks',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 1'
);
"""

_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS rag_chunks_ai AFTER INSERT ON rag_chunks BEGIN
      INSERT INTO rag_chunks_fts(rowid, text) VALUES (new.id, new.text);
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS rag_chunks_ad AFTER DELETE ON rag_chunks BEGIN
      INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS rag_chunks_au AFTER UPDATE ON rag_chunks BEGIN
      INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
      INSERT INTO rag_chunks_fts(rowid, text) VALUES (new.id, new.text);
    END;
    """,
]


def ensure_rag_fts(engine: Engine) -> None:
    """Create FTS virtual table and triggers; backfill missing rows."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        conn.execute(text(_FTS_DDL))
        for stmt in _TRIGGERS:
            conn.execute(text(stmt))
        conn.execute(
            text(
                """
                INSERT INTO rag_chunks_fts(rowid, text)
                SELECT id, text FROM rag_chunks
                WHERE NOT EXISTS (
                    SELECT 1 FROM rag_chunks_fts WHERE rag_chunks_fts.rowid = rag_chunks.id
                )
                """
            )
        )
