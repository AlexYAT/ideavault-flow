"""FTS over RAG chunks (MVP); replace with vector search behind same function signatures later."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.fts_query import build_fts_match


def search_rag_chunks(
    db: Session,
    query: str,
    *,
    current_project: str | None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Retrieve chunk hits scoped by project rules:

    - If ``current_project`` is set: chunks for that project **or** global KB (``project`` NULL).
    - If unset: only global KB chunks (``project`` NULL).
    """
    match_expr = build_fts_match(query)
    if match_expr is None:
        return []
    base_sql = """
        SELECT rag_chunks.id AS chunk_id,
               rag_chunks.text AS text,
               rag_chunks.project AS chunk_project,
               rag_documents.source_uri AS source_uri,
               rag_documents.title AS title
        FROM rag_chunks_fts
        JOIN rag_chunks ON rag_chunks.id = rag_chunks_fts.rowid
        JOIN rag_documents ON rag_documents.id = rag_chunks.document_id
        WHERE rag_chunks_fts MATCH :q
    """
    params: dict[str, Any] = {"q": match_expr, "lim": limit}
    if current_project is not None:
        base_sql += " AND (rag_chunks.project = :proj OR rag_chunks.project IS NULL)"
        params["proj"] = current_project
    else:
        base_sql += " AND rag_chunks.project IS NULL"
    base_sql += " ORDER BY bm25(rag_chunks_fts) LIMIT :lim"
    rows = db.execute(text(base_sql), params).mappings().all()
    return [dict(r) for r in rows]
