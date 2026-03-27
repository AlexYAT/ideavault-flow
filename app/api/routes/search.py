"""FTS search endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.search import SearchItemsOut
from app.services import mvp_api_service

router = APIRouter()


@router.get(
    "/search",
    response_model=SearchItemsOut,
    summary="Full-text search",
    description=(
        "FTS5 over note bodies with conversational token normalization. "
        "Scoped ``project`` includes that project and rows with NULL project."
    ),
)
def search(
    q: str = Query(..., min_length=1, description="Search string"),
    project: str | None = Query(None, description="Optional scope: this project + unassigned notes"),
    db: Session = Depends(get_db),
) -> SearchItemsOut:
    """
    Full-text search over ``items.text``.

    If ``project`` is set: that project plus rows with ``project IS NULL``.
    If omitted: all items.
    """
    hits = mvp_api_service.search_items(db, q, project=project)
    return SearchItemsOut(query=q, items=list(hits))
