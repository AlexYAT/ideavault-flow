"""Thin retrieval façade (FTS today; vector backend tomorrow)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.rag_search_repo import search_rag_chunks


def retrieve(
    db: Session,
    query: str,
    *,
    current_project: str | None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return chunk-level hits with ``source_uri`` and ``title`` for citation."""
    return search_rag_chunks(db, query, current_project=current_project, limit=limit)
