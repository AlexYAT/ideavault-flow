"""Format RAG replies for Telegram (grounded snippets + sources; optional note hints)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.rag.retriever import retrieve
from app.services.search_service import scoped_search


def answer_rag(
    db: Session,
    *,
    question: str,
    current_project: str | None,
    include_item_hints: bool = True,
    max_chunks: int = 6,
) -> str:
    """
    Return a Telegram-ready message with chunk excerpts and source labels.

    If nothing matches the knowledge base, returns an honest empty message.
    """
    q = question.strip()
    if not q:
        return "Введите вопрос текстом."
    hits = retrieve(db, q, current_project=current_project, limit=max_chunks)
    if not hits:
        return (
            "По базе знаний ничего не найдено.\n"
            "Проверьте: /index (переиндексация), папку data/knowledge/, привязку /rag_bind."
        )
    lines: list[str] = ["📚 RAG (фрагменты базы знаний):", ""]
    for i, h in enumerate(hits, 1):
        snippet = (h.get("text") or "").strip().replace("\n", " ")
        if len(snippet) > 400:
            snippet = snippet[:397] + "…"
        title = h.get("title") or "документ"
        uri = h.get("source_uri") or ""
        lines.append(f"{i}. {snippet}")
        lines.append(f"   └ Источник: {title} — {uri}")
        lines.append("")
    if include_item_hints and current_project is not None:
        notes = scoped_search(
            db,
            q,
            current_project=current_project,
            user_has_project=True,
        )
        if notes:
            lines.append("Связанные заметки (vault):")
            for n in notes[:2]:
                t = n.text.strip().replace("\n", " ")
                if len(t) > 160:
                    t = t[:157] + "…"
                lines.append(f"• {t}")
    return "\n".join(lines).rstrip()
