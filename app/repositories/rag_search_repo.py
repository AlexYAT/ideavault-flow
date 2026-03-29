"""FTS over RAG chunks (MVP); replace with vector search behind same function signatures later."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.utils.fts_query import fts_and_terms, fts_or_terms, normalize_fts_query_text
from app.utils.query_normalize import fallback_tokens_if_empty, meaningful_search_tokens

_log = logging.getLogger(__name__)


def _rag_search_tokens(query: str) -> list[str]:
    """Токены для RAG-FTS: как в чат-поиске заметок, без служебных слов инструкций."""
    base = normalize_fts_query_text(query)
    tokens = meaningful_search_tokens(base)
    if not tokens:
        tokens = fallback_tokens_if_empty(base)
    return tokens


def _execute_rag_fts(
    db: Session,
    *,
    match_expr: str,
    proj_scope: str | None,
    limit: int,
) -> list[Any]:
    if not match_expr.strip():
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
    if proj_scope is not None:
        base_sql += " AND (rag_chunks.project = :proj OR rag_chunks.project IS NULL)"
        params["proj"] = proj_scope
    else:
        base_sql += " AND rag_chunks.project IS NULL"
    base_sql += " ORDER BY bm25(rag_chunks_fts) LIMIT :lim"
    return db.execute(text(base_sql), params).mappings().all()


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

    FTS: сначала AND по «осмысленным» токенам (без стоп-слов и шума); при 0 строк — OR по тем же токенам.
    """
    proj_scope = (current_project or "").strip() or None
    tokens = _rag_search_tokens(query)
    if not tokens:
        if get_settings().rag_retrieval_debug:
            _log.warning(
                "RAG_E2E_DEBUG TEMP search_rag_chunks raw_query=%r no_tokens_after_filter proj_scope=%r",
                query,
                proj_scope,
            )
        return []

    expr_and = fts_and_terms(tokens)
    used_expr: str | None = None
    used_fallback_or = False
    rows: list[Any] = []
    if expr_and:
        rows = list(_execute_rag_fts(db, match_expr=expr_and, proj_scope=proj_scope, limit=limit))
        used_expr = expr_and
    if not rows and len(tokens) > 1:
        expr_or = fts_or_terms(tokens)
        if expr_or:
            rows = list(_execute_rag_fts(db, match_expr=expr_or, proj_scope=proj_scope, limit=limit))
            used_expr = expr_or
            used_fallback_or = True

    if get_settings().rag_retrieval_debug:
        top = [(r["chunk_id"], r["title"]) for r in rows[:5]]
        _log.warning(
            "RAG_E2E_DEBUG TEMP search_rag_chunks raw_query=%r normalized_whitespace=%r "
            "rag_tokens=%r fts_match_expr=%r fts_fallback_or=%s proj_scope=%r n_rows=%s top_chunk_id_title=%s",
            query,
            normalize_fts_query_text(query),
            tokens,
            used_expr,
            used_fallback_or,
            proj_scope,
            len(rows),
            top,
        )
    return [dict(r) for r in rows]
