"""Full-text search over items via SQLite FTS5."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def search_fts(
    db: Session,
    query: str,
    *,
    project: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Execute FTS against `items_fts` joined to `items`.

    TODO:
    - bind project + global-null semantics from chat/capture rules
    - use bm25() for ranking when available
              - parameterize query safely (FTS syntax)
    """
    # TODO: escape user input for FTS special characters; use parameterized match
    base_sql = """
        SELECT items.id, items.text, items.project
        FROM items_fts
        JOIN items ON items.id = items_fts.rowid
        WHERE items_fts MATCH :q
    """
    params: dict[str, Any] = {"q": query, "lim": limit}
    if project is not None:
        base_sql += " AND (items.project = :proj OR items.project IS NULL)"
        params["proj"] = project
    base_sql += " ORDER BY bm25(items_fts) LIMIT :lim"
    stmt = text(base_sql)
    rows = db.execute(stmt, params).mappings().all()
    return [dict(r) for r in rows]
