"""Thin read helpers for HTTP API: delegates to existing repos/services (no extra business rules)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.tables import Item
from app.repositories import items_repo, rag_repo
from app.schemas.search import SearchHit
from app.schemas.stats import VaultStatsOut
from app.services import project_service
from app.services.project_snapshot_service import format_project_review
from app.services.search_service import scoped_search


def get_all_items(db: Session, *, project: str | None = None, limit: int = 100) -> list[Item]:
    """Recent items, newest first (same semantics as :func:`~app.repositories.items_repo.list_items`)."""
    return list(items_repo.list_items(db, project=project, limit=limit))


def search_items(db: Session, query: str, *, project: str | None = None) -> list[SearchHit]:
    """
    Full-text search over ``items.text``.

    If ``project`` is set: that project plus rows with ``project IS NULL``.
    If omitted: all items.
    """
    if project is not None:
        return scoped_search(
            db,
            query,
            current_project=project,
            user_has_project=True,
        )
    return scoped_search(
        db,
        query,
        current_project=None,
        user_has_project=False,
    )


def list_projects(db: Session) -> list[str]:
    """Distinct non-null project names from items, sorted."""
    return project_service.list_distinct_projects(db)


def review_project(db: Session, *, project: str | None = None) -> str:
    """Project snapshot text (same pipeline as Telegram ``/review``: deterministic + optional LLM)."""
    return format_project_review(db, current_project=project)


def get_vault_stats(db: Session) -> VaultStatsOut:
    """Cheap aggregates over ``items`` + RAG tables for demo endpoints."""
    names = items_repo.list_distinct_project_names(db)
    return VaultStatsOut(
        items_total=items_repo.count_items_total(db),
        projects_total=len(names),
        items_with_project=items_repo.count_items_with_nonnull_project(db),
        rag_documents_total=rag_repo.count_documents(db),
        rag_chunks_total=rag_repo.count_chunks(db),
        rag_projects_with_docs=rag_repo.count_projects_with_documents(db),
    )
