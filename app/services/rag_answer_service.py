"""Format RAG replies for Telegram (grounded snippets + sources; optional note hints)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.rag.retriever import retrieve
from app.schemas.search import SearchHit
from app.services.llm_enhancement import try_enhance_rag_answer
from app.services.search_service import scoped_search

_MAX_RAG_REPLY_LEN = 3900


def _deterministic_rag_reply(
    db: Session,
    *,
    question: str,
    current_project: str | None,
    hits: list[dict],
    include_item_hints: bool,
    vault_notes_cached: list[SearchHit] | None = None,
) -> str:
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
        notes = vault_notes_cached
        if notes is None:
            notes = scoped_search(
                db,
                question,
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


def answer_rag(
    db: Session,
    *,
    question: str,
    current_project: str | None,
    include_item_hints: bool = True,
    max_chunks: int = 6,
) -> str:
    """
    Сообщение для чата в режиме RAG: при ``LLM_ENABLED`` ответ проходит через LLM (grounded или no_hits).

    Иначе — только детерминированная разметка фрагментов, как раньше.
    """
    q = question.strip()
    if not q:
        return "Введите вопрос текстом."
    hits = retrieve(db, q, current_project=current_project, limit=max_chunks)

    vault_notes_cached: list[SearchHit] | None = None
    if include_item_hints and current_project is not None:
        vault_notes_cached = list(
            scoped_search(
                db,
                q,
                current_project=current_project,
                user_has_project=True,
            )[:2],
        )
    vault_hint_lines = (
        [n.text.strip() for n in vault_notes_cached] if vault_notes_cached else None
    )

    settings = get_settings()
    if not settings.llm_enabled:
        return _deterministic_rag_reply(
            db,
            question=q,
            current_project=current_project,
            hits=hits,
            include_item_hints=include_item_hints,
            vault_notes_cached=vault_notes_cached,
        )

    enhanced = try_enhance_rag_answer(
        settings,
        question=q,
        current_project=current_project,
        chunks=hits,
        vault_hint_lines=vault_hint_lines,
    )
    if enhanced:
        text = enhanced.strip()
        if len(text) > _MAX_RAG_REPLY_LEN:
            text = text[: _MAX_RAG_REPLY_LEN - 3] + "..."
        return text

    return _deterministic_rag_reply(
        db,
        question=q,
        current_project=current_project,
        hits=hits,
        include_item_hints=include_item_hints,
        vault_notes_cached=vault_notes_cached,
    )
