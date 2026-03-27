"""Append-only chat turns linked to :class:`~app.db.tables.ChatThread`."""

from sqlalchemy.orm import Session

from app.db.tables import ChatMessage


def append_turn(db: Session, *, thread_id: int, user_text: str, assistant_text: str) -> None:
    """Record one user question and bot reply (two rows)."""
    db.add(ChatMessage(thread_id=thread_id, role="user", content=user_text))
    db.add(ChatMessage(thread_id=thread_id, role="assistant", content=assistant_text))
    db.commit()
