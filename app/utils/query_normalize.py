"""
Lightweight query normalization for conversational text (RU/EN).

No external NLP — stopword trimming + token length so FTS is not forced to match
filler words like «что», «у меня», «по» together with real keywords.
"""

from __future__ import annotations

import re
import unicodedata

# Conversational / question words (RU + common EN). Keep list small and maintainable.
_STOPWORDS: frozenset[str] = frozenset(
    {
        # Russian
        "что",
        "как",
        "где",
        "когда",
        "куда",
        "почему",
        "зачем",
        "кто",
        "чем",
        "какой",
        "какая",
        "какие",
        "какого",
        "каком",
        "какую",
        "этот",
        "эта",
        "это",
        "эти",
        "тот",
        "та",
        "те",
        "то",
        "все",
        "всё",
        "нет",
        "да",
        "ли",
        "не",
        "ни",
        "уж",
        "у",
        "и",
        "а",
        "но",
        "бы",
        "же",
        "либо",
        "или",
        "для",
        "про",
        "при",
        "над",
        "под",
        "из",
        "со",
        "во",
        "без",
        "до",
        "от",
        "до",
        "за",
        "к",
        "в",
        "на",
        "с",
        "о",
        "об",
        "ко",
        "по",
        "из",
        "у",
        "меня",
        "тебя",
        "нас",
        "вас",
        "мне",
        "тебе",
        "нему",
        "ней",
        "них",
        "мой",
        "моя",
        "моё",
        "мои",
        "твой",
        "наш",
        "ваш",
        "их",
        "его",
        "её",
        "их",
        "я",
        "ты",
        "он",
        "она",
        "оно",
        "мы",
        "вы",
        "они",
        "есть",
        "было",
        "были",
        "был",
        "была",
        "будет",
        "мне",
        "нам",
        "вам",
        "тут",
        "там",
        "только",
        "уже",
        "ещё",
        "еще",
        "какие",
        "такой",
        "такая",
        "такое",
        "такие",
        "очень",
        "ещё",
        # phrasing
        "расскажи",
        "покажи",
        "найди",
        "ищи",
        "скажи",
        "подскажи",
        "сохранено",
        "записано",
        "лежит",
        "проекту",
        "проекта",
        "проекте",
        "проектам",
        # English
        "what",
        "which",
        "who",
        "where",
        "when",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "me",
        "my",
        "we",
        "you",
        "it",
        "its",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "any",
        "some",
        "there",
        "here",
        "about",
        "with",
        "from",
        "into",
        "for",
        "over",
        "and",
        "or",
        "not",
        "no",
        "yes",
        "this",
        "that",
        "these",
        "those",
    }
)

# Letters (incl. Cyrillic), digits, internal hyphens/apostrophes inside a token
_TOKEN_RE = re.compile(r"[\w\-']+", re.UNICODE)


def meaningful_search_tokens(text: str, *, min_len: int = 2) -> list[str]:
    """
    Lowercase, strip punctuation, drop stopwords and very short tokens.

    ``min_len`` uses Unicode character count (not bytes) after NFKC normalization.
    """
    if not text or not text.strip():
        return []
    normalized = unicodedata.normalize("NFKC", text.lower())
    raw_tokens = _TOKEN_RE.findall(normalized)
    out: list[str] = []
    for t in raw_tokens:
        t = t.strip("-'")
        if len(t) < min_len:
            continue
        if t in _STOPWORDS:
            continue
        out.append(t)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def fallback_tokens_if_empty(text: str, *, min_len: int = 3) -> list[str]:
    """
    If everything was filtered as noise, take longer alphanumeric tokens only (still no stopwords).
    """
    base = meaningful_search_tokens(text, min_len=min_len)
    if base:
        return base
    normalized = unicodedata.normalize("NFKC", text.lower())
    raw_tokens = _TOKEN_RE.findall(normalized)
    out: list[str] = []
    for t in raw_tokens:
        t = t.strip("-'")
        if len(t) < min_len or t in _STOPWORDS:
            continue
        out.append(t)
    seen: set[str] = set()
    unique: list[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique
