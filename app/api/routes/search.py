"""FTS search endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.search import SearchHit
from app.services.search_service import scoped_search

router = APIRouter()


@router.get("/search", response_model=list[SearchHit])
def search(
    q: str = Query(..., min_length=1),
    project: str | None = None,
    db: Session = Depends(get_db),
) -> list[SearchHit]:
    """
    Search vault text via FTS.

    If `project` is set: match that project and global (NULL project) rows.
    If omitted: search across all items.

    TODO: auth; derive default project from Telegram session.
    """
    if project is not None:
        return scoped_search(
            db,
            q,
            current_project=project,
            user_has_project=True,
        )
    return scoped_search(
        db,
        q,
        current_project=None,
        user_has_project=False,
    )
