"""Full-text search over items via SQLite FTS5."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.fts_query import build_fts_match


def search_fts_match(
    db: Session,
    match_expr: str,
    *,
    project: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Execute FTS with a pre-built MATCH expression (caller ensures safety/quoting)."""
    if not match_expr.strip():
        return []
    base_sql = """
        SELECT items.id, items.text, items.project
        FROM items_fts
        JOIN items ON items.id = items_fts.rowid
        WHERE items_fts MATCH :q
    """
    params: dict[str, Any] = {"q": match_expr, "lim": limit}
    if project is not None:
        base_sql += " AND (items.project = :proj OR items.project IS NULL)"
        params["proj"] = project
    base_sql += " ORDER BY bm25(items_fts) LIMIT :lim"
    stmt = text(base_sql)
    rows = db.execute(stmt, params).mappings().all()
    return [dict(r) for r in rows]


def search_fts(
    db: Session,
    query: str,
    *,
    project: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Run FTS using :func:`build_fts_match` on raw ``query`` string."""
    match_expr = build_fts_match(query)
    if match_expr is None:
        return []
    return search_fts_match(db, match_expr, project=project, limit=limit)
