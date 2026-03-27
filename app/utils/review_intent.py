"""Lightweight heuristics for broad project Q&A (no LLM)."""

from __future__ import annotations

import re
import unicodedata

from app.utils.query_normalize import meaningful_search_tokens


def normalize_for_intent(text: str) -> str:
    """Lower + Unicode NFKC for stable substring checks."""
    return unicodedata.normalize("NFKC", text.lower())


def extract_mentioned_project(text: str, project_names: list[str]) -> str | None:
    """
    If the message contains a known project name as a whole token / token group, return it.

    Longer names are checked first to reduce ambiguity (e.g. ``a`` vs ``a-long-name``).
    """
    if not project_names or not text.strip():
        return None
    n = normalize_for_intent(text)
    for name in sorted(project_names, key=len, reverse=True):
        pattern = re.escape(name.lower())
        if re.search(rf"(?<!\w){pattern}(?!\w)", n, re.UNICODE):
            return name
    return None


def is_broad_project_query(text: str) -> bool:
    """
    Detect inventory-style questions («что сохранено», «какие идеи по проекту») where FTS often misses.

    Uses substring hints and low keyword-token count as a fallback signal.
    """
    raw = text.strip()
    if not raw:
        return False
    n = normalize_for_intent(text)
    hints = (
        "проект",
        "идеи",
        "идея",
        "замет",
        "сохран",
        "записан",
        "обзор",
        "последн",
        "в проекте",
    )
    if any(h in n for h in hints):
        return True
    toks = meaningful_search_tokens(text)
    # Long question with almost no searchable tokens → likely chit-chat inventory
    return len(toks) <= 1 and len(n) >= 14
