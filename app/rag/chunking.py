"""Character-based chunking with overlap (MVP; no token counting)."""

from __future__ import annotations


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """
    Split ``text`` into overlapping windows for FTS indexing.

    Empty / whitespace-only input yields no chunks.
    """
    raw = text.strip()
    if not raw:
        return []
    if len(raw) <= max_chars:
        return [raw]
    chunks: list[str] = []
    start = 0
    while start < len(raw):
        end = min(start + max_chars, len(raw))
        piece = raw[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(raw):
            break
        start = max(0, end - overlap)
    return chunks
