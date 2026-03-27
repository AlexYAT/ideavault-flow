"""OpenAI audio transcription (Whisper-class models via REST)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


def transcribe_audio_file(path: Path, settings: Settings) -> str | None:
    """
    Return transcript text or ``None`` on missing key / HTTP error.

    Expects a readable audio file (``.oga``, ``.mp3``, etc.) as produced by Telegram.
    """
    key = (getattr(settings, "openai_api_key", "") or "").strip()
    if not key:
        logger.info("stt skipped: no OPENAI_API_KEY")
        return None
    model = getattr(settings, "openai_stt_model", "whisper-1") or "whisper-1"
    timeout = float(getattr(settings, "stt_timeout_seconds", 60.0) or 60.0)
    try:
        with path.open("rb") as audio_fp, httpx.Client(timeout=timeout) as client:
            files = {"file": (path.name, audio_fp, "application/octet-stream")}
            data = {"model": model}
            resp = client.post(
                OPENAI_TRANSCRIPTIONS_URL,
                headers={"Authorization": f"Bearer {key}"},
                files=files,
                data=data,
            )
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning("stt failed: %s", type(exc).__name__)
        return None
    text = payload.get("text") if isinstance(payload, dict) else None
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None
