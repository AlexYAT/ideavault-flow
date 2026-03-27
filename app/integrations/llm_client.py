"""Optional OpenAI Chat Completions client (httpx). Retrieval stays upstream."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

import httpx

from app.integrations.llm_logging import LLMRequestLogInfo

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIChatClient:
    """Minimal chat completion wrapper; failures return ``None`` (caller falls back)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float = 0.2,
        max_tokens: int = 200,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model_name(self) -> str:
        return self._model

    @staticmethod
    def from_settings(settings: Settings) -> OpenAIChatClient | None:
        """Backward-compatible: client only. Prefer :func:`resolve_llm_client` for skip reason."""
        client, _reason = resolve_llm_client(settings)
        return client

    def complete(
        self,
        *,
        system: str,
        user: str,
        log_info: LLMRequestLogInfo,
        debug: bool = False,
    ) -> tuple[str | None, str | None]:
        """
        Return ``(assistant_text, None)`` on success, or ``(None, reason)`` on failure.

        Reasons match observability taxonomy: ``timeout``, ``http_error``, ``invalid_response``,
        ``unexpected_exception``. Emits ``llm_request_*`` logs (never secrets or full prompt/response).
        """
        prompt_len = len(system) + len(user)
        extra_debug = ""
        if debug:
            prev = log_info.query_preview or ""
            ids = ",".join(str(i) for i in log_info.note_ids[:30]) if log_info.note_ids else ""
            extra_debug = f" query_preview={prev!r} note_ids=[{ids}] prompt_chars={prompt_len}"

        logger.info(
            "llm event=llm_request_started mode=%s scope=%s notes_count=%d model=%s "
            "temperature=%.2f max_tokens=%d debug=%s%s",
            log_info.mode,
            log_info.scope,
            log_info.notes_count,
            self._model,
            self._temperature,
            self._max_tokens,
            debug,
            extra_debug,
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    elapsed_ms = (time.monotonic() - t0) * 1000.0
                    logger.warning(
                        "llm event=llm_request_failed mode=%s scope=%s reason=http_error "
                        "status=%s latency_ms=%.1f notes_count=%d",
                        log_info.mode,
                        log_info.scope,
                        resp.status_code,
                        elapsed_ms,
                        log_info.notes_count,
                    )
                    return None, "http_error"
                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    elapsed_ms = (time.monotonic() - t0) * 1000.0
                    logger.warning(
                        "llm event=llm_request_failed mode=%s scope=%s reason=invalid_response "
                        "detail=json_decode latency_ms=%.1f",
                        log_info.mode,
                        log_info.scope,
                        elapsed_ms,
                    )
                    return None, "invalid_response"

            choice = data.get("choices", [{}])[0] if isinstance(data, dict) else {}
            msg = (choice.get("message") or {}).get("content")
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            if isinstance(msg, str) and msg.strip():
                text = msg.strip()
                logger.info(
                    "llm event=llm_request_success mode=%s scope=%s latency_ms=%.1f "
                    "response_chars=%d notes_count=%d model=%s",
                    log_info.mode,
                    log_info.scope,
                    elapsed_ms,
                    len(text),
                    log_info.notes_count,
                    self._model,
                )
                return text, None

            logger.warning(
                "llm event=llm_request_failed mode=%s scope=%s reason=invalid_response "
                "detail=empty_content latency_ms=%.1f",
                log_info.mode,
                log_info.scope,
                elapsed_ms,
            )
            return None, "invalid_response"

        except httpx.TimeoutException:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            logger.warning(
                "llm event=llm_request_failed mode=%s scope=%s reason=timeout "
                "latency_ms=%.1f notes_count=%d",
                log_info.mode,
                log_info.scope,
                elapsed_ms,
                log_info.notes_count,
            )
            return None, "timeout"
        except httpx.RequestError as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            logger.warning(
                "llm event=llm_request_failed mode=%s scope=%s reason=http_error "
                "detail=%s latency_ms=%.1f",
                log_info.mode,
                log_info.scope,
                type(exc).__name__,
                elapsed_ms,
            )
            return None, "http_error"
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            logger.warning(
                "llm event=llm_request_failed mode=%s scope=%s reason=unexpected_exception "
                "detail=%s latency_ms=%.1f",
                log_info.mode,
                log_info.scope,
                type(exc).__name__,
                elapsed_ms,
            )
            return None, "unexpected_exception"


def resolve_llm_client(settings: Settings) -> tuple[OpenAIChatClient | None, str | None]:
    """
    Return ``(client, None)`` if LLM may run, else ``(None, reason)``.

    Skip reasons: ``disabled``, ``no_key``. Does not log here — callers log ``llm_skipped``.
    """
    if not getattr(settings, "llm_enabled", False):
        return None, "disabled"
    key = (getattr(settings, "openai_api_key", "") or "").strip()
    if not key:
        return None, "no_key"
    client = OpenAIChatClient(
        api_key=key,
        model=getattr(settings, "openai_model", "gpt-4o-mini") or "gpt-4o-mini",
        timeout_seconds=float(getattr(settings, "llm_timeout_seconds", 25.0) or 25.0),
        temperature=float(getattr(settings, "llm_temperature", 0.2)),
        max_tokens=int(getattr(settings, "llm_max_tokens", 200)),
    )
    return client, None
