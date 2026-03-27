"""FTS search endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.search import SearchItemsOut
from app.services import mvp_api_service

router = APIRouter()


@router.get("/search", response_model=SearchItemsOut)
def search(
    q: str = Query(..., min_length=1),
    project: str | None = None,
    db: Session = Depends(get_db),
) -> SearchItemsOut:
    """
    Full-text search over ``items.text``.

    If ``project`` is set: that project plus rows with ``project IS NULL``.
    If omitted: all items.
    """
    hits = mvp_api_service.search_items(db, q, project=project)
    return SearchItemsOut(query=q, items=list(hits))
