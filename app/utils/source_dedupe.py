"""Deduplicate search hits by normalized text + project (for Telegram / API UX)."""

import re
import unicodedata

from app.schemas.search import SearchHit


def normalize_text_for_dedupe(text: str) -> str:
    """NFKC lowercase and single spaces for near-duplicate detection."""
    t = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", t).strip()


def normalize_note_text(text: str) -> str:
    """
    Normalized body for capture-time duplicate checks.

    Same rules as :func:`normalize_text_for_dedupe` (lowercase, trim, collapsed spaces).
    """
    return normalize_text_for_dedupe(text)


def dedupe_search_hits(sources: list[SearchHit], *, max_n: int | None = None) -> list[SearchHit]:
    """
    Drop hits that share the same normalized body text and ``project``.

    If ``max_n`` is set, stop after that many distinct hits (order preserved).
    """
    seen: set[tuple[str, str | None]] = set()
    out: list[SearchHit] = []
    for s in sources:
        key = (normalize_text_for_dedupe(s.text), s.project)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if max_n is not None and len(out) >= max_n:
            break
    return out
