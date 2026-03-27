"""Deterministic «/next» suggestions from note text (no LLM)."""

from sqlalchemy.orm import Session

from app.repositories import items_repo


def _load_corpus(db: Session, *, current_project: str | None, limit: int = 50) -> tuple[str, int]:
    """Lowercased joined texts and note count for the active scope."""
    if current_project is not None:
        rows = list(items_repo.list_items(db, project=current_project, limit=limit))
    else:
        rows = list(items_repo.list_items(db, project=None, limit=limit))
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
    """Telegram-ready multiline message."""
    steps = suggest_next_actions(db, current_project=current_project)
    header = "Дальше (по эвристикам из заметок):"
    body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, start=1))
    return f"{header}\n{body}"
