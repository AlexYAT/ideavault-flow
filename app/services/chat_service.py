"""Formatted replies for free-text vault queries (e.g. Telegram chat mode)."""

from sqlalchemy.orm import Session

from app.services.review_service import review_ask_stub

_MAX_MESSAGE_LEN = 3900


def answer_text_query(
    db: Session,
    user_id: str,
    message: str,
    current_project: str | None,
) -> str:
    """
    Run the same retrieval path as ``/api/review/ask`` and return a single reply string.

    ``user_id`` is reserved for future personalization; scope is ``current_project``.
    """
    _ = user_id
    result = review_ask_stub(db, message, current_project=current_project)
    parts: list[str] = [result.answer]
    if result.sources:
        parts.append("")
        parts.append("Источники:")
        for src in result.sources[:3]:
            line = src.text.strip().replace("\n", " ")
            if len(line) > 120:
                line = line[:117] + "..."
            parts.append(f"• [{src.id}] {line}")
    if result.next_steps:
        parts.append("")
        parts.append("Дальше:")
        for step in result.next_steps[:3]:
            parts.append(f"• {step}")
    text = "\n".join(parts)
    if len(text) > _MAX_MESSAGE_LEN:
        text = text[: _MAX_MESSAGE_LEN - 3] + "..."
    return text
