"""Append-only chat turns linked to :class:`~app.db.tables.ChatThread`."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import ChatMessage


def append_turn(db: Session, *, thread_id: int, user_text: str, assistant_text: str) -> None:
    """Record one user question and bot reply (two rows)."""
    db.add(ChatMessage(thread_id=thread_id, role="user", content=user_text))
    db.add(ChatMessage(thread_id=thread_id, role="assistant", content=assistant_text))
    db.commit()


def list_recent_messages_for_thread(db: Session, thread_id: int, *, limit: int = 200) -> list[ChatMessage]:
    """Последние ``limit`` сообщений потока в хронологическом порядке (старые → новые)."""
    rows = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit),
        ).all(),
    )
    rows.reverse()
    return rows
