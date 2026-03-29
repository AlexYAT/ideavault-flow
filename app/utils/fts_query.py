"""Build safe SQLite FTS5 MATCH expressions from user-provided text."""

import re
import unicodedata


def normalize_fts_query_text(query: str) -> str:
    """
    Привести произвольный запрос к виду, ближе к токенам FTS: NFKC, нижний регистр,
    дефисы → пробелы, схлопывание пробелов. Не трогает кавычки — их обрабатывает вызывающий код.
    """
    t = unicodedata.normalize("NFKC", query or "")
    t = t.lower()
    t = t.replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


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
    Convert free text into an FTS5 expression: AND of quoted tokens (split on whitespace).

    Перед разбором строка нормализуется (:func:`normalize_fts_query_text`), чтобы запросы вроде
    ``ideavault-flow`` давали те же токены, что «IdeaVault Flow» в проиндексированном тексте.

    For conversational queries prefer :func:`fts_and_terms` on
    :func:`app.utils.query_normalize.meaningful_search_tokens`.
    """
    cleaned = normalize_fts_query_text(query)
    if not cleaned:
        return None
    cleaned = cleaned.replace('"', " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    return fts_and_terms(tokens)
