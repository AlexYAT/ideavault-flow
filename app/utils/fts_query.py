"""Build safe SQLite FTS5 MATCH expressions from user-provided text."""

import re


def build_fts_match(query: str) -> str | None:
    """
    Convert free text into an FTS5 expression: AND of quoted tokens.

    Reduces broken MATCH syntax and accidental operator injection. Returns ``None``
    when there is nothing usable to search (caller should return an empty result set).
    """
    cleaned = query.strip()
    if not cleaned:
        return None
    # drop double-quotes; remaining tokens are quoted individually
    cleaned = cleaned.replace('"', " ")
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    parts: list[str] = []
    for token in tokens:
        # Remove characters that commonly break MATCH or act as FTS5 syntax
        safe = re.sub(r'[\*:^"()]', "", token)
        if not safe:
            continue
        escaped = safe.replace('"', '""')
        parts.append(f'"{escaped}"')
    if not parts:
        return None
    return " AND ".join(parts)
