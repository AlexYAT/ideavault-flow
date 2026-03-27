"""Download Telegram voice files into ``data/voice/<scope>/``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from telegram import Voice
from telegram.ext import ExtBot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VOICE_ROOT = PROJECT_ROOT / "data" / "voice"


def voice_destination_dir(current_project: str | None) -> Path:
    """Per-project subfolder (sanitized) or ``_global``."""
    if not current_project:
        seg = "_global"
    else:
        seg = "".join(c if c.isalnum() or c in "-_" else "_" for c in current_project.strip())[:80] or "_global"
    d = VOICE_ROOT / seg
    d.mkdir(parents=True, exist_ok=True)
    return d


def build_voice_filename(voice: Voice) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ext = "oga"
    if voice.mime_type and "mpeg" in voice.mime_type:
        ext = "mp3"
    return f"{ts}_{voice.file_unique_id}.{ext}"


async def download_voice_to_path(bot: ExtBot, voice: Voice, dest: Path) -> None:
    """Fetch file from Telegram and write to ``dest``."""
    tg_file = await bot.get_file(voice.file_id)
    await tg_file.download_to_drive(dest)
