"""Optional OpenAI vision (one short Russian caption); returns None if skipped or on error."""

from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)
_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def try_describe_image(
    settings: Settings,
    *,
    image_bytes: bytes,
    mime_type: str,
    user_caption: str | None,
) -> str | None:
    """
    If LLM is configured, request a short grounded visual description.

    Does not log images or keys. On any failure returns ``None`` (caller uses MVP fallback).
    """
    if not getattr(settings, "llm_enabled", False):
        return None
    key = (getattr(settings, "openai_api_key", "") or "").strip()
    if not key:
        return None

    mime = (mime_type or "image/jpeg").split(";")[0].strip()
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    instruction = (
        "Одно или два коротких предложения по-русски: что на изображении, для личной заметки. "
        "Только наблюдаемое; не выдумывай контекст."
    )
    if user_caption:
        instruction += f" Учти подпись пользователя как контекст (не цитируй дословно): {user_caption}"

    payload = {
        "model": getattr(settings, "openai_model", "gpt-4o-mini") or "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": min(180, int(getattr(settings, "llm_max_tokens", 200) or 200)),
        "temperature": float(getattr(settings, "llm_temperature", 0.2)),
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        timeout = float(getattr(settings, "llm_timeout_seconds", 25.0) or 25.0)
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.info("llm vision skipped or failed: %s", type(exc).__name__)
        return None

    try:
        choice = data.get("choices", [{}])[0]
        msg = (choice.get("message") or {}).get("content")
    except (TypeError, AttributeError):
        return None
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    return None
