"""Build safe SQLite FTS5 MATCH expressions from user-provided text."""

import re


def _quote_fts_term(token: str) -> str | None:
    """Sanitize a single token and return a quoted FTS5 phrase term, or ``None`` if empty."""
    safe = re.sub(r'[\*:^"()]', "", token)
    if not safe:
        return None
    escaped = safe.replace('"', '""')
    return f'"{escaped}"'


def fts_and_terms(tokens: list[str]) -> str | None:
    """AND of quoted tokens (all must match)."""
    parts: list[str] = []
    for token in tokens:
        q = _quote_fts_term(token)
        if q:
            parts.append(q)
    if not parts:
        return None
    return " AND ".join(parts)


def fts_or_terms(tokens: list[str]) -> str | None:
    """OR of quoted tokens (any may match)."""
    parts: list[str] = []
    for token in tokens:
        q = _quote_fts_term(token)
        if q:
            parts.append(q)
    if not parts:
        return None
    return " OR ".join(parts)


def build_fts_match(query: str) -> str | None:
    """
    Convert free text into an FTS5 expression: AND of quoted tokens (raw split).

    For conversational queries prefer :func:`fts_and_terms` on
    :func:`app.utils.query_normalize.meaningful_search_tokens`.
    """
    cleaned = query.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace('"', " ")
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    return fts_and_terms(tokens)
