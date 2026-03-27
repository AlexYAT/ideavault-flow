"""MVP review flow: retrieve via FTS and return stub answer (no LLM)."""

from sqlalchemy.orm import Session

from app.schemas.review import ReviewAskResponse
from app.services.search_service import scoped_search


def review_ask_stub(
    db: Session,
    message: str,
    *,
    current_project: str | None,
) -> ReviewAskResponse:
    """
    Search the vault for ``message`` and return a short summary plus sources.

    Scope matches HTTP search: with ``current_project``, include that project and
    global (NULL) rows; otherwise search all items.
    """
    has_project = current_project is not None
    hits = scoped_search(
        db,
        message,
        current_project=current_project,
        user_has_project=has_project,
    )
    if not hits:
        return ReviewAskResponse(
            answer="По базе ничего не нашлось — попробуйте другие слова или расширьте область (/clear).",
            sources=[],
            next_steps=[
                "Добавьте заметку с «+ текст».",
                "Сбросьте проект командой /clear, чтобы искать по всем записям.",
            ],
        )

    n = len(hits)
    if n == 1:
        lead = "Нашёл одну релевантную запись."
    else:
        lead = f"Нашёл релевантных записей: {n}."

    first = hits[0].text.strip().replace("\n", " ")
    if len(first) > 140:
        first = first[:137] + "…"
    answer = f"{lead} Первая по релевантности: {first}"

    next_steps = [
        "Откройте запись в API или уточните запрос, если это не то.",
        "Используйте /set <проект>, чтобы сузить поиск.",
    ]
    return ReviewAskResponse(answer=answer, sources=list(hits), next_steps=next_steps)
