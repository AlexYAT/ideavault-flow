"""Retrieve-and-generate over local SQLite context."""

from sqlalchemy.orm import Session

from app.services.search_service import scoped_search


def answer_with_context(
    db: Session,
    user_message: str,
    *,
    current_project: str | None,
    user_has_project: bool,
) -> str:
    """
    Placeholder RAG response using retrieved FTS rows.

    TODO: call LLM with citations, chunking, safety filters.
    """
    hits = scoped_search(
        db,
        user_message,
        current_project=current_project,
        user_has_project=user_has_project,
    )
    if not hits:
        return "No matching items in the vault yet. TODO: friendlier assistant copy."
    lines = [f"- [{h.id}] {h.text[:200]}" for h in hits[:5]]
    return "Context from your vault:\n" + "\n".join(lines)
