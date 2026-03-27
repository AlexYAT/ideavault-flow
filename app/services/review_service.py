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
    Search the vault for ``message`` and return a short stub summary plus sources.

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
            answer="По базе ничего не найдено",
            sources=[],
            next_steps=["Добавьте новую заметку", "Уточните запрос"],
        )

    preview = []
    for h in hits[:5]:
        snippet = h.text.strip().replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        preview.append(f"[{h.id}] {snippet}")

    answer = (
        "Найдено записей: "
        f"{len(hits)}. Кратко: "
        + " | ".join(preview)
    )
    next_steps = [
        "Откройте найденные записи в списке и уточните статус.",
        "Сузьте область поиска параметром project, если результатов слишком много.",
        "Добавьте заметку с ключевыми словами, если контекста не хватает.",
    ]
    return ReviewAskResponse(answer=answer, sources=list(hits), next_steps=next_steps)
