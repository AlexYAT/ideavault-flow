"""System prompts and user message builders for grounded LLM calls."""

from __future__ import annotations

from app.schemas.search import SearchHit


SYSTEM_CHAT = """Ты помощник IdeaVault. Отвечай только на основе предоставленных заметок.
Если данных недостаточно — напрямую скажи, что в заметках этого нет.
Не выдумывай факты. Без таблиц markdown. Кратко, по делу, удобно для Telegram (несколько коротких абзацев или буллетов)."""


SYSTEM_REVIEW = """Ты помогаешь кратко описать состояние проекта по списку заметок.
Используй только переданные заметки и эвристические «пробелы». Не добавляй факты снаружи.
Без markdown-таблиц. Кратко: фокус, темы, пробелы — по-русски, практично."""


SYSTEM_NEXT = """Ты предлагаешь 3–5 следующих шагов строго на основе приведённых заметок.
Каждый шаг — конкретное действие. Без общих фраз без привязки к текстам. Нумерация 1. 2. 3.
Если заметок мало, скажи об этом и дай минимум осмысленных шагов из того, что есть."""


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
        "Ответь на вопрос."
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
        "Дай короткий снимок: фокус, заметные темы, пробелы — только из этого."
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
        f"Базовые эвристические шаги (можно улучшить формулировку, не меняя смысл без оснований в заметках):\n{heur}\n\n"
        "Сформулируй 3–5 следующих шагов."
    )
