"""Deterministic «/next» suggestions; optional LLM rewrite grounded in notes."""

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.tables import Item
from app.repositories import items_repo
from app.services.llm_enhancement import try_enhance_next


def _rows_for_scope(db: Session, *, current_project: str | None, limit: int = 50) -> list[Item]:
    if current_project is not None:
        return list(items_repo.list_items(db, project=current_project, limit=limit))
    return list(items_repo.list_items(db, project=None, limit=limit))


def _load_corpus(db: Session, *, current_project: str | None, limit: int = 50) -> tuple[str, int]:
    """Lowercased joined texts and note count for the active scope."""
    rows = _rows_for_scope(db, current_project=current_project, limit=limit)
    return " ".join(r.text.lower() for r in rows), len(rows)


def suggest_next_actions(db: Session, *, current_project: str | None) -> list[str]:
    """
    Return 3–5 concrete next steps from keyword heuristics, ordered by relevance.

    Sparse vault → short generic guidance (still actionable).
    """
    corpus, n = _load_corpus(db, current_project=current_project)
    actions: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        if text not in seen and len(actions) < 5:
            seen.add(text)
            actions.append(text)

    if n == 0:
        return [
            "Добавьте первую заметку: + одна мысль на строку.",
            "Задайте проект: /set <имя>, чтобы шаги были привязаны к контексту.",
            "После 2–3 заметок снова нажмите /next.",
        ]

    # Keyword-driven (RU + EN fragments)
    if "mvp" in corpus:
        add("Уточнить формулировку MVP и критерий «готово».")
    if "иде" in corpus or "idea" in corpus:
        add("Выбрать одну идею и расписать 3 следующих шага.")
    if "пользовател" in corpus or "юзер" in corpus or "customer" in corpus or "сценари" in corpus:
        add("Собрать 3 коротких пользовательских сценария (до/во время/после).")
    if "монет" in corpus or "деньг" in corpus or "pricing" in corpus or "тариф" in corpus:
        add("Проверить гипотезу монетизации: кто платит и за что.")
    if "этап" in corpus or "phase" in corpus or "итерац" in corpus:
        add("Разбить реализацию на этапы и назвать текущий.")
    if "review" in corpus or "ревью" in corpus or "обзор" in corpus:
        add("Запланировать ревью прогресса и критерии приёмки.")
    if "телеграм" in corpus or "telegram" in corpus or "бот" in corpus:
        add("Прогнать один полный пользовательский сценарий в боте.")

    # Fill to at least 3
    generic_pool = [
        "Зафиксировать один риск и способ его снять.",
        "Сформулировать ближайший измеримый результат на 1–2 недели.",
        "Свериться с /review: совпадает ли фокус с последними заметками.",
    ]
    for g in generic_pool:
        add(g)
        if len(actions) >= 3:
            break

    while len(actions) < 3:
        add("Добавьте заметку с конкретным вопросом или ограничением.")

    return actions[:5]


def format_next_message(db: Session, *, current_project: str | None) -> str:
    """Telegram-ready multiline message; optional LLM if notes exist and LLM on."""
    steps = suggest_next_actions(db, current_project=current_project)
    baseline_header = "Дальше (по эвристикам из заметок):"
    baseline = f"{baseline_header}\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, start=1))

    rows = _rows_for_scope(db, current_project=current_project, limit=30)
    if not rows:
        return baseline

    note_lines = [r.text.strip().replace("\n", " ") for r in rows[:20]]
    enhanced = try_enhance_next(
        get_settings(),
        current_project=current_project,
        note_lines=note_lines,
        heuristic_steps=steps,
        source_note_ids=tuple(r.id for r in rows[:20]),
    )
    return enhanced if enhanced else baseline
