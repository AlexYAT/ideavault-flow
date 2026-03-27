"""Telegram chat mode: non-capture messaging and next-step hints."""

from sqlalchemy.orm import Session

from app.services.rag_service import answer_with_context


def handle_chat_message(
    db: Session,
    _user_id: str,
    text: str,
    *,
    current_project: str | None,
) -> str:
    """
    Free-form chat over vault data.

    TODO: persist chat turns, rate limits, command routing.
    """
    has_project = current_project is not None
    return answer_with_context(
        db,
        text,
        current_project=current_project,
        user_has_project=has_project,
    )


def suggest_next_steps(
    db: Session,
    *,
    current_project: str | None,
) -> list[str]:
    """
    Short actionable follow-ups after review/RAG.

    TODO: derive from item status distribution, deadlines, user goals.
    """
    _ = (db, current_project)
    return [
        "Capture 3 new '+' items for your top idea.",
        "Run /review to triage inbox items.",
        "Use /set <project> to narrow RAG scope.",
    ]
