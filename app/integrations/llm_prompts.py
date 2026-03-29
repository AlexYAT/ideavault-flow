"""System prompts and user message builders for grounded LLM calls."""

from __future__ import annotations

from typing import Any

from app.schemas.search import SearchHit


SYSTEM_CHAT = """Ты помощник IdeaVault в Telegram. Отвечай только по переданным заметкам. Не выдумывай факты.
Если по заметкам ответить нельзя или данных мало — скажи это прямо одной короткой фразой (например: «В заметках этого нет» / «Недостаточно заметок»), без воды и извинений.

Формат ответа (строго):
— Не больше трёх коротких абзацев ИЛИ трёх буллетов (не раздувай).
— Первая строка — прямой ответ на вопрос из заметок (суть по делу).
— Дальше только необходимые детали из тех же заметок.

Запрещено: формулировки «В заметках указано, что…», «Однако…», «В целом…», пустой общий тон, markdown-таблицы, любые факты не из заметок."""


SYSTEM_CHAT_NO_SOURCES = """Ты помощник IdeaVault. По запросу пользователя в заметках текущей области проекта релевантного ничего не найдено (или списка заметок для опоры нет).
Не выдумывай факты о проекте. Ответ максимально короткий и практичный (обычно 2–4 предложения):
— Явно скажи, что в заметках/материалах проекта по этому запросу ничего нет.
— Если вопрос общий и не требует данных проекта — можно ответить кратко по смыслу.
— Предложи: уточнить формулировку, добавить заметки (в т.ч. через + в боте) или материалы в data/knowledge.
Без длинных рассуждений, без markdown-таблиц, без вымышленных деталей проекта."""


SYSTEM_RAG_GROUNDED = """Ты помощник IdeaVault в режиме RAG. Отвечай только по переданным фрагментам базы знаний и (если есть отдельным блоком) по коротким связанным заметкам. Не придумывай источники, цитаты и факты вне фрагментов.
Формат: 2–4 коротких предложения или до 4 буллетов; при необходимости укажи номер фрагмента из списка. Без таблиц, без воды."""


SYSTEM_RAG_NO_HITS = """Ты помощник IdeaVault (RAG). По запросу пользователя в проиндексированной базе знаний проекта релевантных фрагментов не найдено.
Не выдумывай содержимое файлов и документов проекта. Ответ короткий (2–4 предложения):
— Сообщи, что в базе знаний по запросу ничего не найдено.
— Упоминай при необходимости: переиндексацию, папку data/knowledge/, привязку GitHub (rag_bind).
— Если вопрос общий — можно кратко ответить вне контекста проекта.
Без длинных рассуждений."""


SYSTEM_REVIEW = """Ты готовишь короткий снимок для Telegram только из переданных строк (фокус, свежие заметки, эвристические пробелы). Не добавляй фактов снаружи. Без markdown-таблиц.

Формат ответа — только три блока с такими заголовками (кратко, без вступлений и без других разделов):

Фокус:
<1–2 строки по смыслу переданного фокуса>

Темы:
<1–3 пункта — что следует из заметок>

Пробелы:
<1–3 пункта из переданных эвристических пробелов; если их не было — «—»>

Не пиши комментариев вроде «вот краткий обзор» или итогов после блоков."""


SYSTEM_NEXT = """Ты формулируешь следующие шаги строго из приведённых заметок (и базовых эвристических пунктов как опоры). Не выдумывай продукт и контекст.

Формат ответа:
— Только нумерованный список из 3–5 пунктов: «1. …», «2. …» и т.д.
— Каждый пункт — короткое actionable действие.
— Без вступительных предложений до списка и без заключения после списка.
— Без подзаголовков и без маркированных списков — только нумерация.

Если заметок мало, всё равно дай 3–5 пунктов максимально из имеющегося текста; при необходимости один пункт может быть «Зафиксировать в заметке: …»."""


def _scope_label(current_project: str | None) -> str:
    if current_project:
        return f"текущий проект: «{current_project}»"
    return "область: все заметки (проект не задан)"


def format_notes_block(
    sources: list[SearchHit],
    *,
    max_items: int = 8,
    max_chars_per_note: int = 400,
) -> str:
    """Compact numbered list for prompts (IDs for traceability)."""
    lines: list[str] = []
    for i, s in enumerate(sources[:max_items], start=1):
        t = s.text.strip().replace("\n", " ")
        if len(t) > max_chars_per_note:
            t = t[: max_chars_per_note - 1] + "…"
        proj = f" [проект: {s.project}]" if s.project else ""
        lines.append(f"{i}. (id {s.id}){proj} {t}")
    return "\n".join(lines)


def build_chat_user_prompt(
    question: str,
    current_project: str | None,
    sources: list[SearchHit],
) -> str:
    """User message for grounded Q&A over retrieved hits."""
    scope = _scope_label(current_project)
    notes = format_notes_block(sources)
    return (
        f"Вопрос пользователя: {question}\n"
        f"Контекст области: {scope}\n\n"
        f"Заметки (используй только их):\n{notes}\n\n"
        "Ответь на вопрос по правилам из system: сначала суть одной строкой, не больше трёх абзацев или буллетов, без запрещённых формулировок."
    )


def build_chat_no_sources_user_prompt(question: str, current_project: str | None) -> str:
    """User message когда ретривал заметок пустой, но LLM должен ответить честно."""
    scope = _scope_label(current_project)
    return (
        f"Вопрос пользователя: {question}\n"
        f"Контекст области: {scope}\n\n"
        "Релевантных заметок для опоры нет. Ответь строго по правилам из system."
    )


def _format_rag_chunks_for_prompt(chunks: list[dict[str, Any]], *, max_chunks: int = 8) -> str:
    lines: list[str] = []
    for i, h in enumerate(chunks[:max_chunks], start=1):
        snippet = (h.get("text") or "").strip().replace("\n", " ")
        if len(snippet) > 500:
            snippet = snippet[:497] + "…"
        title = h.get("title") or "документ"
        uri = h.get("source_uri") or ""
        lines.append(f"{i}. {snippet}\n   Источник: {title} — {uri}")
    return "\n\n".join(lines) if lines else "(нет фрагментов)"


def build_rag_grounded_user_prompt(
    question: str,
    current_project: str | None,
    chunks: list[dict[str, Any]],
    vault_hint_lines: list[str] | None = None,
) -> str:
    scope = _scope_label(current_project)
    block = _format_rag_chunks_for_prompt(chunks)
    hints = ""
    if vault_hint_lines:
        hl = "\n".join(f"• {t[:300]}{'…' if len(t) > 300 else ''}" for t in vault_hint_lines[:4])
        hints = f"\n\nСвязанные заметки (vault, вторичный контекст):\n{hl}\n"
    return (
        f"Вопрос пользователя: {question}\n"
        f"Область: {scope}\n\n"
        f"Фрагменты базы знаний (опора для ответа):\n{block}\n"
        f"{hints}\n"
        "Ответь по правилам из system."
    )


def build_rag_no_hits_user_prompt(question: str, current_project: str | None) -> str:
    scope = _scope_label(current_project)
    return (
        f"Вопрос пользователя: {question}\n"
        f"Область: {scope}\n\n"
        "Фрагменты из индекса RAG не найдены. Ответь строго по правилам из system."
    )


def build_review_user_prompt(
    focus_line: str,
    n_notes: int,
    snippets: list[str],
    gap_bullets: list[str],
) -> str:
    """User message for /review-style snapshot."""
    snip = "\n".join(f"• {s}" for s in snippets) if snippets else "(нет строк)"
    gaps = "\n".join(f"• {g}" for g in gap_bullets) if gap_bullets else "(нет)"
    return (
        f"{focus_line}\n"
        f"Число заметок в области: {n_notes}\n\n"
        f"Свежие заметки:\n{snip}\n\n"
        f"Эвристические пробелы (ориентир, не истина):\n{gaps}\n\n"
        "Выведи только блоки «Фокус:», «Темы:», «Пробелы:» по правилам из system, без лишнего текста."
    )


def build_next_user_prompt(
    current_project: str | None,
    note_lines: list[str],
    heuristic_steps: list[str],
) -> str:
    """User message for /next enhancement."""
    scope = _scope_label(current_project)
    notes = "\n".join(f"• {t}" for t in note_lines[:20]) if note_lines else "(пусто)"
    heur = "\n".join(f"• {h}" for h in heuristic_steps[:5])
    return (
        f"Область: {scope}\n\n"
        f"Заметки:\n{notes}\n\n"
        f"Базовые эвристические шаги (опора для формулировок; не расширяй смысл без заметок):\n{heur}\n\n"
        "Сформулируй 3–5 следующих шагов по правилам из system: только нумерованный список 1.–5., без вступления."
    )
