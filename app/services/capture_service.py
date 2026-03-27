"""Telegram/API capture flow: persist '+' items with project context."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.enums import CaptureSource, ChatMode, ItemPriority, ItemStatus
from app.core.mode_detector import detect_mode, strip_capture_prefix
from app.repositories import items_repo
from app.utils.source_dedupe import normalize_note_text


@dataclass(frozen=True)
class CaptureResult:
    """Outcome of a capture attempt (new row or existing duplicate)."""

    item_id: int
    is_duplicate: bool


def capture_from_text(
    db: Session,
    *,
    raw_text: str,
    current_project: str | None,
    source: CaptureSource = CaptureSource.TELEGRAM_TEXT,
    raw_payload_ref: str | None = None,
) -> CaptureResult | None:
    """
    If ``raw_text`` is capture mode, return item id (new or existing duplicate).

    Returns ``None`` if the message is not capture mode or if the note body is empty.
    Duplicate = same :func:`normalize_note_text` and same ``project`` (including ``NULL``).
    """
    if detect_mode(raw_text) != ChatMode.CAPTURE:
        return None
    body = strip_capture_prefix(raw_text).strip()
    if not body:
        return None

    normalized = normalize_note_text(body)
    existing = items_repo.find_item_by_normalized_text(
        db,
        normalized_text=normalized,
        project=current_project,
    )
    if existing is not None:
        return CaptureResult(item_id=existing.id, is_duplicate=True)

    row = items_repo.create_item(
        db,
        text=body,
        project=current_project,
        status=ItemStatus.NEW.value,
        priority=ItemPriority.NORMAL.value,
        source=source.value,
        raw_payload_ref=raw_payload_ref,
    )
    return CaptureResult(item_id=row.id, is_duplicate=False)
