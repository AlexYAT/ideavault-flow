"""Review workflow: RAG-ish summary and next-step suggestions."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services import chat_service

router = APIRouter()


class ReviewRequest(BaseModel):
    """Ask assistant using vault context. TODO: thread id, tone, language."""

    user_id: str = Field(..., description="Logical user key (Telegram id as string)")
    message: str = Field(..., min_length=1)
    current_project: str | None = None


@router.post("/review/ask")
def review_ask(body: ReviewRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Return placeholder RAG reply plus static next steps."""
    reply = chat_service.handle_chat_message(
        db,
        body.user_id,
        body.message,
        current_project=body.current_project,
    )
    steps = chat_service.suggest_next_steps(db, current_project=body.current_project)
    return {"reply": reply, "next_steps": steps}
