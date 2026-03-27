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
    Run the same retrieval path as ``/api/review/ask`` and return one Telegram-friendly string.

    ``user_id`` is reserved for future personalization; scope is ``current_project``.
    """
    _ = user_id
    result = review_ask_stub(db, message, current_project=current_project)
    parts: list[str] = [result.answer]

    if result.sources:
        parts.append("")
        for src in result.sources[:3]:
            line = src.text.strip().replace("\n", " ")
            if len(line) > 100:
                line = line[:97] + "…"
            proj = f" · {src.project}" if src.project else ""
            parts.append(f"• {line}{proj}")

    if result.next_steps:
        parts.append("")
        parts.append(result.next_steps[0])

    text = "\n".join(parts)
    if len(text) > _MAX_MESSAGE_LEN:
        text = text[: _MAX_MESSAGE_LEN - 3] + "..."
    return text
