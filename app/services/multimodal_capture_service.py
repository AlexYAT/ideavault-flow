"""
MVP multimodal capture: image (+ optional caption) → one note in ``items``.

Vision (OpenAI Chat Completions with ``image_url``) runs only when ``LLM_ENABLED``
and ``OPENAI_API_KEY`` are set; otherwise a transparent text fallback is used so
:mod:`app.integrations.llm_vision_optional` stays swappable for other providers later.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.enums import CaptureSource, ItemPriority, ItemStatus
from app.integrations.llm_vision_optional import try_describe_image
from app.repositories import items_repo

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

# Declared MIME + sniff fallbacks (no extra deps).
_ALLOWED_MAIN_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)


def normalize_caption(caption: str | None) -> str:
    """Strip user caption; empty string if missing."""
    return (caption or "").strip()


def validate_image_bytes(*, data: bytes, declared_type: str | None, filename: str | None) -> str:
    """
    Ensure bytes look like a supported image; return canonical ``image/...`` for downstream use.

    Raises:
        ValueError: empty payload, unknown format, or type mismatch.
    """
    if not data:
        raise ValueError("Empty image payload")
    sniff = _sniff_image_mime(data)
    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared in ("image/jpg",):
        declared = "image/jpeg"
    if sniff is None:
        raise ValueError(
            f"File «{filename or 'upload'}» is not a supported image (jpeg/png/webp/gif)",
        )
    if declared and declared in _ALLOWED_MAIN_TYPES and declared != sniff:
        # Browser sometimes mislabels; prefer magic bytes.
        logger.debug("Declared Content-Type %s differs from sniffed %s; using sniffed", declared, sniff)
    return sniff


def build_capture_text(
    settings: Settings,
    *,
    image_bytes: bytes,
    content_type: str,
    filename: str | None,
    caption: str | None,
) -> tuple[str, bool]:
    """
    Compose ``items.text`` for this capture.

    Returns:
        ``(capture_text, used_vision)`` — ``used_vision`` is True if OpenAI vision returned text.
    """
    cap = normalize_caption(caption)
    label = filename or "image"

    vision = try_describe_image(
        settings,
        image_bytes=image_bytes,
        mime_type=content_type,
        user_caption=cap or None,
    )
    if vision:
        if cap:
            return f"{cap}\n\n[Авто-описание изображения] {vision}", True
        return f"[Авто-описание изображения] {vision}", True

    if cap:
        return f"{cap}\n\n[Вложение: изображение «{label}», {len(image_bytes)} байт]", False
    return (
        f"[Фото] «{label}», {len(image_bytes)} байт. Подпись не указана — кратко опишите смысл "
        f"самостоятельно. (Vision выключен или недоступен — включите LLM и ключ для авто-описания.)",
        False,
    )


def persist_capture(
    db: Session,
    *,
    project: str | None,
    capture_text: str,
) -> int:
    """Insert one item; returns new id."""
    row = items_repo.create_item(
        db,
        text=capture_text,
        project=project,
        status=ItemStatus.NEW.value,
        priority=ItemPriority.NORMAL.value,
        source=CaptureSource.API_IMAGE.value,
        raw_payload_ref=None,
    )
    return row.id


def _sniff_image_mime(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
