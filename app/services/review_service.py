"""MVP review flow: FTS retrieval, project overview fallback, no LLM."""

from sqlalchemy.orm import Session

from app.repositories import items_repo
from app.schemas.review import ReviewAskResponse
from app.schemas.search import SearchHit
from app.services.search_service import scoped_search
from app.utils.review_intent import extract_mentioned_project, is_broad_project_query
from app.utils.source_dedupe import dedupe_search_hits

_MAX_KEYWORD_SOURCES = 18


def _keyword_answer(hits: list[SearchHit]) -> str:
    """One-line lead + first hit preview for keyword mode."""
    n = len(hits)
    if n == 1:
        lead = "Нашёл одну релевантную запись."
    else:
        lead = f"Нашёл релевантных записей: {n}."
    first = hits[0].text.strip().replace("\n", " ")
    if len(first) > 140:
        first = first[:137] + "…"
    return f"{lead} Первая по релевантности: {first}"


def review_ask_stub(
    db: Session,
    message: str,
    *,
    current_project: str | None,
) -> ReviewAskResponse:
    """
    Search the vault, then optionally show a project inventory for broad questions.

    If the text names an existing project (substring token match), that project
    drives FTS scope before falling back to ``current_project``.
    """
    project_names = items_repo.list_distinct_project_names(db)
    mentioned = extract_mentioned_project(message, project_names)
    search_project = mentioned or current_project
    has_scope = search_project is not None

    hits = scoped_search(
        db,
        message,
        current_project=search_project,
        user_has_project=has_scope,
    )
    hits = dedupe_search_hits(hits)

    if hits:
        return ReviewAskResponse(
            answer=_keyword_answer(hits),
            sources=hits[:_MAX_KEYWORD_SOURCES],
            next_steps=[
                "Откройте запись в API или уточните запрос, если это не то.",
                "Используйте /set <проект>, чтобы сузить поиск.",
            ],
        )

    if is_broad_project_query(message) and search_project is not None:
        total = items_repo.count_by_project(db, project=search_project)
        rows = items_repo.list_items(db, project=search_project, limit=5)
        overview_hits = dedupe_search_hits(
            [
                SearchHit(id=r.id, text=r.text, project=r.project)
                for r in rows
            ],
            max_n=3,
        )
        if total == 0:
            return ReviewAskResponse(
                answer=f"В проекте «{search_project}» пока нет заметок.",
                sources=[],
                next_steps=[
                    "Добавьте заметку: + текст",
                    f"Проверьте имя проекта или /set {search_project}",
                ],
            )
        answer = (
            f"По проекту «{search_project}» записей: {total}. Последние:"
        )
        return ReviewAskResponse(
            answer=answer,
            sources=overview_hits,
            next_steps=[
                "Спросите конкретнее (например по ключевому слову), чтобы сузить выборку.",
                "Добавьте новую заметку с «+», если нужно зафиксировать идею.",
            ],
        )

    return ReviewAskResponse(
        answer="По базе ничего не нашлось — попробуйте другие слова или расширьте область (/clear).",
        sources=[],
        next_steps=[
            "Добавьте заметку с «+ текст».",
            "Сбросьте проект командой /clear, чтобы искать по всем записям.",
        ],
    )
