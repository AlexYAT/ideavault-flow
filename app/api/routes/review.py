"""Review workflow: stub Q&A over vault search (no LLM)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.review import ReviewAskRequest, ReviewAskResponse
from app.services.review_service import review_ask_stub

router = APIRouter()


@router.post("/review/ask", response_model=ReviewAskResponse)
def review_ask(body: ReviewAskRequest, db: Session = Depends(get_db)) -> ReviewAskResponse:
    """Retrieve with FTS and return stub answer, sources, and follow-ups."""
    return review_ask_stub(
        db,
        body.message,
        current_project=body.current_project,
    )
