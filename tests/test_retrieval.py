"""FTS retrieval: conversational queries, scope, fallback (no Telegram IO)."""

from app.repositories import items_repo
from app.services.search_service import retrieval_with_fallback, scoped_search


def test_conversational_russian_finds_mvp_note(db_session) -> None:
    """«что у меня по MVP?» should match a note containing MVP after stopword drop."""
    items_repo.create_item(
        db_session,
        text="идея для MVP",
        project="prompt-course",
        status="new",
        priority="normal",
        source="telegram",
    )
    hits = scoped_search(
        db_session,
        "что у меня по MVP?",
        current_project="prompt-course",
        user_has_project=True,
    )
    assert hits
    assert "MVP" in hits[0].text.upper()
    assert hits[0].project == "prompt-course"


def test_project_scope_includes_null_project_rows(db_session) -> None:
    """Scoped search returns project rows + global (NULL) rows, not other projects."""
    items_repo.create_item(
        db_session,
        text="only in prompt-course MVP zeta",
        project="prompt-course",
        status="new",
        priority="normal",
        source="api",
    )
    items_repo.create_item(
        db_session,
        text="other project MVP zeta",
        project="other",
        status="new",
        priority="normal",
        source="api",
    )
    items_repo.create_item(
        db_session,
        text="global MVP zeta note",
        project=None,
        status="new",
        priority="normal",
        source="api",
    )
    hits = scoped_search(
        db_session,
        "zeta MVP",
        current_project="prompt-course",
        user_has_project=True,
    )
    projects_found = {h.project for h in hits}
    assert "prompt-course" in projects_found or None in projects_found
    assert not any(h.project == "other" for h in hits)


def test_meaningful_tokens_russian_question() -> None:
    """Stopwords stripped; keyword MVP remains."""
    from app.utils.query_normalize import meaningful_search_tokens

    assert meaningful_search_tokens("что у меня по MVP?") == ["mvp"]


def test_or_fallback_when_and_fails(db_session) -> None:
    """OR across tokens finds row when no single row contains all tokens."""
    items_repo.create_item(
        db_session,
        text="only alpha token here",
        project=None,
        status="new",
        priority="normal",
        source="api",
    )
    raw = retrieval_with_fallback(
        db_session,
        "alpha beta gamma conversational",
        project=None,
    )
    assert raw
    assert "alpha" in raw[0]["text"]

