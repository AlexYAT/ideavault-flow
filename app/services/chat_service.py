"""Formatted replies for free-text vault queries (e.g. Telegram chat mode)."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.review import ReviewAskResponse
from app.services.llm_enhancement import try_enhance_chat
from app.services.review_service import review_ask_stub
from app.utils.source_dedupe import dedupe_search_hits

_MAX_MESSAGE_LEN = 3900
_MAX_TELEGRAM_SOURCES = 3


def _deterministic_reply(result: ReviewAskResponse) -> str:
    """Pre-LLM Telegram formatting (sources + one next step)."""
    parts: list[str] = [result.answer]

    distinct = dedupe_search_hits(result.sources, max_n=_MAX_TELEGRAM_SOURCES)
    if distinct:
        parts.append("")
        for src in distinct:
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


def answer_text_query(
    db: Session,
    user_id: str,
    message: str,
    current_project: str | None,
) -> str:
    """
    Retrieve with ``review_ask_stub``, then optionally rephrase via LLM if enabled and notes exist.

    No notes, LLM off, or LLM failure → deterministic formatting unchanged.
    """
    _ = user_id
    result = review_ask_stub(db, message, current_project=current_project)
    baseline = _deterministic_reply(result)

    enhanced = try_enhance_chat(
        get_settings(),
        message=message,
        current_project=current_project,
        sources=result.sources,
    )
    if enhanced:
        capped = enhanced if len(enhanced) <= _MAX_MESSAGE_LEN else enhanced[: _MAX_MESSAGE_LEN - 3] + "..."
        return capped
    return baseline
