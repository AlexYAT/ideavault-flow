"""System prompts and user message builders for grounded LLM calls."""

from __future__ import annotations

from app.schemas.search import SearchHit


SYSTEM_CHAT = """Ты помощник IdeaVault в Telegram. Отвечай только по переданным заметкам. Не выдумывай факты.
Если по заметкам ответить нельзя или данных мало — скажи это прямо одной короткой фразой (например: «В заметках этого нет» / «Недостаточно заметок»), без воды и извинений.

Формат ответа (строго):
— Не больше трёх коротких абзацев ИЛИ трёх буллетов (не раздувай).
— Первая строка — прямой ответ на вопрос из заметок (суть по делу).
— Дальше только необходимые детали из тех же заметок.

Запрещено: формулировки «В заметках указано, что…», «Однако…», «В целом…», пустой общий тон, markdown-таблицы, любые факты не из заметок."""


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
