"""Safe, structured fields for LLM observability (no secrets)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMRequestLogInfo:
    """Context for one Chat Completions call (logged, never includes API key or full bodies)."""

    mode: str  # chat | review | next
    scope: str  # global or project name
    notes_count: int
    model: str
    query_preview: str | None = None  # e.g. user question (debug)
    note_ids: tuple[int, ...] = ()  # optional, debug


def format_scope(current_project: str | None) -> str:
    """Stable scope label for logs."""
    return current_project if current_project else "global"


def truncate_preview(text: str, max_len: int = 120) -> str:
    """Single-line preview for logs (no newlines)."""
    t = text.replace("\n", " ").replace("\r", " ").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"
