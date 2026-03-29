"""Сохранение фото из Telegram в ``data/telegram_photos/<scope>/`` (без vision/OCR)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from telegram import PhotoSize
from telegram.ext import ExtBot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHOTO_ROOT = PROJECT_ROOT / "data" / "telegram_photos"


def photo_destination_dir(current_project: str | None) -> Path:
    """Подпапка по проекту (как у voice) или ``_global``."""
    if not current_project:
        seg = "_global"
    else:
        seg = (
            "".join(c if c.isalnum() or c in "-_" else "_" for c in current_project.strip())[:80]
            or "_global"
        )
    d = PHOTO_ROOT / seg
    d.mkdir(parents=True, exist_ok=True)
    return d


def pick_largest_photo(sizes: list[PhotoSize]) -> PhotoSize:
    """Берём вариант наибольшего размера (по ``file_size``, иначе по площади)."""
    return max(
        sizes,
        key=lambda p: (p.file_size or 0, (p.width or 0) * (p.height or 0)),
    )


def build_photo_filename(photo: PhotoSize) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{photo.file_unique_id}.jpg"


async def download_photo_to_path(bot: ExtBot, photo: PhotoSize, dest: Path) -> None:
    tg_file = await bot.get_file(photo.file_id)
    await tg_file.download_to_drive(dest)
