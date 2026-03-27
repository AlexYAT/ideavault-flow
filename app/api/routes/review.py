"""Review: FTS Q&A stub (POST) and project snapshot (GET, same as bot ``/review``)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.review import ReviewAskRequest, ReviewAskResponse, ReviewSnapshotResponse
from app.services import mvp_api_service
from app.services.review_service import review_ask_stub

router = APIRouter()


@router.get("/review", response_model=ReviewSnapshotResponse)
def review_snapshot(
    project: str | None = Query(None, description="Scope to this project; omit for all notes"),
    db: Session = Depends(get_db),
) -> ReviewSnapshotResponse:
    """Compact snapshot over notes in scope (deterministic + optional LLM)."""
    text = mvp_api_service.review_project(db, project=project)
    return ReviewSnapshotResponse(project=project, review=text)


@router.post("/review/ask", response_model=ReviewAskResponse)
def review_ask(body: ReviewAskRequest, db: Session = Depends(get_db)) -> ReviewAskResponse:
    """Retrieve with FTS and return stub answer, sources, and follow-ups."""
    return review_ask_stub(
        db,
        body.message,
        current_project=body.current_project,
    )
