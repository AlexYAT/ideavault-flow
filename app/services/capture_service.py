"""Telegram/API capture flow: persist '+' items with project context."""

from sqlalchemy.orm import Session

from app.core.enums import CaptureSource, ChatMode, ItemPriority, ItemStatus
from app.core.mode_detector import detect_mode, strip_capture_prefix
from app.repositories import items_repo


def capture_from_text(
    db: Session,
    *,
    raw_text: str,
    current_project: str | None,
    source: CaptureSource = CaptureSource.TELEGRAM_TEXT,
    raw_payload_ref: str | None = None,
) -> int | None:
    """
    If `raw_text` is capture mode, persist and return new item id.

    TODO: photo captions, voice transcripts, dedupe, auto-tags.
    """
    if detect_mode(raw_text) != ChatMode.CAPTURE:
        return None
    body = strip_capture_prefix(raw_text)
    row = items_repo.create_item(
        db,
        text=body,
        project=current_project,
        status=ItemStatus.INBOX.value,
        priority=ItemPriority.NORMAL.value,
        source=source.value,
        raw_payload_ref=raw_payload_ref,
    )
    return row.id
