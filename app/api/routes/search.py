"""FTS search endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.search import SearchOut
from app.services.search_service import scoped_search

router = APIRouter()


@router.get("/search", response_model=SearchOut)
def search(
    q: str = Query(..., min_length=1),
    project: str | None = None,
    db: Session = Depends(get_db),
) -> SearchOut:
    """
    Full-text search over ``items.text``.

    If ``project`` is set: that project plus rows with ``project IS NULL``.
    If omitted: all items.
    """
    if project is not None:
        hits = scoped_search(
            db,
            q,
            current_project=project,
            user_has_project=True,
        )
    else:
        hits = scoped_search(
            db,
            q,
            current_project=None,
            user_has_project=False,
        )
    return SearchOut(hits=list(hits))
