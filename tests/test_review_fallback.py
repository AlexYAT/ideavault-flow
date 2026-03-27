"""Broad project queries, mentioned project, source deduplication."""

from app.repositories import items_repo
from app.schemas.search import SearchHit
from app.services import chat_service, review_service
from app.utils.source_dedupe import dedupe_search_hits


def test_dedupe_identical_notes(db_session) -> None:
    """Two rows with the same text/project produce one logical source."""
    for _ in range(2):
        items_repo.create_item(
            db_session,
            text="same duplicate body",
            project="demo",
            status="new",
            priority="normal",
            source="api",
        )
    raw = [
        SearchHit(id=1, text="same duplicate body", project="demo"),
        SearchHit(id=2, text="same duplicate body", project="demo"),
    ]
    out = dedupe_search_hits(raw, max_n=3)
    assert len(out) == 1


def test_overview_by_mentioned_project_name(db_session) -> None:
    """Broad question naming the project lists recent rows even when FTS is weak."""
    items_repo.create_item(
        db_session,
        text="идея для MVP",
        project="prompt-course",
        status="new",
        priority="normal",
        source="telegram",
    )
    items_repo.create_item(
        db_session,
        text="вторая строка",
        project="prompt-course",
        status="new",
        priority="normal",
        source="telegram",
    )
    res = review_service.review_ask_stub(
        db_session,
        "что сохранено по prompt-course?",
        current_project=None,
    )
    assert "prompt-course" in res.answer
    assert "записей:" in res.answer or "записей" in res.answer
    assert len(res.sources) >= 1
    texts = {s.text for s in res.sources}
    assert "идея для MVP" in texts or "вторая строка" in texts


def test_broad_ideas_with_current_project_overview(db_session) -> None:
    """«какие идеи по проекту?» + session project triggers inventory fallback."""
    items_repo.create_item(
        db_session,
        text="первая задумка",
        project="course-x",
        status="new",
        priority="normal",
        source="telegram",
    )
    res = review_service.review_ask_stub(
        db_session,
        "какие идеи по проекту?",
        current_project="course-x",
    )
    assert "course-x" in res.answer
    assert res.sources
    assert any("первая задумка" in s.text for s in res.sources)


def test_chat_dedupes_duplicate_hits_in_output(db_session) -> None:
    """Telegram formatting keeps at most one bullet per text+project key."""
    items_repo.create_item(
        db_session,
        text="unique broad overview line",
        project="z",
        status="new",
        priority="normal",
        source="api",
    )
    items_repo.create_item(
        db_session,
        text="unique broad overview line",
        project="z",
        status="new",
        priority="normal",
        source="api",
    )
    out = chat_service.answer_text_query(
        db_session,
        "1",
        "какие идеи по проекту?",
        current_project="z",
    )
    assert out.count("unique broad overview line") == 1
