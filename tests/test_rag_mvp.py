"""MVP RAG: chunk ingest + FTS scope."""

from app.rag import chunking
from app.repositories import rag_repo
from app.repositories.rag_search_repo import search_rag_chunks
from app.services import rag_answer_service


def test_chunking_splits_long_text() -> None:
    text = "word " * 500
    chunks = chunking.chunk_text(text, max_chars=200, overlap=20)
    assert len(chunks) >= 2
    assert all(len(c) <= 200 for c in chunks)


def test_rag_search_scopes_project_vs_global(db_session) -> None:
    body_proj = "UniqueRagMvpToken проектный контекст для задания."
    rag_repo.add_document_with_chunks(
        db_session,
        project="studycase",
        source_type="local",
        source_uri="local:notes.md",
        title="notes.md",
        body=body_proj,
        chunk_texts=chunking.chunk_text(body_proj),
    )
    hits = search_rag_chunks(db_session, "UniqueRagMvpToken", current_project="studycase", limit=5)
    assert hits
    assert hits[0]["source_uri"] == "local:notes.md"

    global_hits = search_rag_chunks(db_session, "UniqueRagMvpToken", current_project=None, limit=5)
    assert global_hits == []

    body_glob = "GlobalUniqueRagToken в общих материалах."
    rag_repo.add_document_with_chunks(
        db_session,
        project=None,
        source_type="local",
        source_uri="local:global.md",
        title="global.md",
        body=body_glob,
        chunk_texts=chunking.chunk_text(body_glob),
    )
    gh = search_rag_chunks(db_session, "GlobalUniqueRagToken", current_project=None, limit=5)
    assert gh


def test_answer_rag_honest_empty(db_session) -> None:
    out = rag_answer_service.answer_rag(
        db_session,
        question="zzznomatchxyz123",
        current_project=None,
        include_item_hints=False,
    )
    assert "ничего не найдено" in out.lower()
