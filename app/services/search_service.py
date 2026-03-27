"""Search orchestration (scope by session / explicit project) with retrieval fallback."""

from sqlalchemy.orm import Session

from app.repositories import search_repo
from app.schemas.search import SearchHit
from app.utils.fts_query import fts_and_terms, fts_or_terms
from app.utils.query_normalize import fallback_tokens_if_empty, meaningful_search_tokens

_MAX_TOKEN_QUERIES = 8


def retrieval_with_fallback(
    db: Session,
    query: str,
    *,
    project: str | None,
    limit: int = 20,
) -> list[dict]:
    """
    FTS retrieval with conversational-friendly steps:

    1. AND of normalized ``meaningful_search_tokens`` (drop filler words).
    2. If empty — OR across those tokens.
    3. If still empty — merge single-token searches (dedupe by id).

    ``project`` scope: ``None`` = all rows; else = that project + ``NULL`` project.
    """
    tokens = meaningful_search_tokens(query)
    if not tokens:
        tokens = fallback_tokens_if_empty(query)
    if not tokens:
        return []

    expr_and = fts_and_terms(tokens)
    if expr_and:
        rows = search_repo.search_fts_match(db, expr_and, project=project, limit=limit)
        if rows:
            return list(rows)

    if len(tokens) > 1:
        expr_or = fts_or_terms(tokens)
        if expr_or:
            rows = search_repo.search_fts_match(db, expr_or, project=project, limit=limit)
            if rows:
                return list(rows)

    order: list[int] = []
    bucket: dict[int, dict] = {}
    for t in tokens[:_MAX_TOKEN_QUERIES]:
        expr = fts_and_terms([t])
        if not expr:
            continue
        rows = search_repo.search_fts_match(db, expr, project=project, limit=limit)
        for r in rows:
            rid = int(r["id"])
            if rid not in bucket:
                bucket[rid] = r
                order.append(rid)
            if len(order) >= limit:
                return [bucket[i] for i in order]
    return [bucket[i] for i in order[:limit]]


def scoped_search(
    db: Session,
    query: str,
    *,
    current_project: str | None,
    user_has_project: bool,
) -> list[SearchHit]:
    """
    Apply capture/chat search scoping rules with conversational query handling.

    - If ``user_has_project`` and ``current_project`` is set: search that project
      plus rows with ``project IS NULL``.
    - Otherwise: search all items.
    """
    project: str | None
    if user_has_project and current_project is not None:
        project = current_project
    else:
        project = None

    raw = retrieval_with_fallback(db, query, project=project)
    return [SearchHit(id=r["id"], text=r["text"], project=r["project"]) for r in raw]
