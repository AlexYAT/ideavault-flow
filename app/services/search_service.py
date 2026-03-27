"""Search orchestration (scope by session / explicit project)."""

from sqlalchemy.orm import Session

from app.repositories import search_repo
from app.schemas.search import SearchHit


def scoped_search(
    db: Session,
    query: str,
    *,
    current_project: str | None,
    user_has_project: bool,
) -> list[SearchHit]:
    """
    Apply capture/chat search scoping rules.

    - If user_has_project: search project-specific rows plus global (NULL project)
    - Else: search all data

    TODO: align with product wording; add pagination.
    """
    if user_has_project and current_project is not None:
        raw = search_repo.search_fts(db, query, project=current_project)
    else:
        raw = search_repo.search_fts(db, query, project=None)
    return [SearchHit(id=r["id"], text=r["text"], project=r["project"]) for r in raw]
