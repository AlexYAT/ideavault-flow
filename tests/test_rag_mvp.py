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


def test_rag_search_strips_project_in_filter(db_session) -> None:
    """Пробелы вокруг имени проекта в фильтре не должны ломать сравнение с rag_chunks.project."""
    body = "StripScopeToken789 в тексте чанка."
    rag_repo.add_document_with_chunks(
        db_session,
        project="studycase",
        source_type="local",
        source_uri="local:x.md",
        title="x.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    hits = search_rag_chunks(
        db_session,
        "StripScopeToken789",
        current_project="  studycase  ",
        limit=5,
    )
    assert hits


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


def test_rag_search_prompt_course_trailing_space_in_filter(db_session) -> None:
    """Имя проекта в фильтре с завершающим пробелом всё ещё совпадает с rag_chunks.project."""
    body = "TrailingPromptCourseToken в документе prompt-course."
    rag_repo.add_document_with_chunks(
        db_session,
        project="prompt-course",
        source_type="local",
        source_uri="local:pc.md",
        title="pc.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    hits = search_rag_chunks(
        db_session,
        "TrailingPromptCourseToken",
        current_project="prompt-course ",
        limit=5,
    )
    assert hits
    assert hits[0]["title"] == "pc.md"


def test_rag_natural_language_opishi_ideavault_finds_chunk(db_session) -> None:
    """Длинная русская фраза с инструкцией («опиши», «или») не ломает FTS: остаются ideavault + flow."""
    body = "Коротко: продукт IdeaVault Flow в рамках курса."
    rag_repo.add_document_with_chunks(
        db_session,
        project="prompt-course",
        source_type="local",
        source_uri="local:nl-opishi.md",
        title="nl-opishi.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    q = "Опиши ideavault-flow или IdeaVault Flow"
    hits = search_rag_chunks(db_session, q, current_project="prompt-course", limit=5)
    assert hits
    assert hits[0]["title"] == "nl-opishi.md"


def test_rag_natural_language_chto_znaesh_pro_ideavault(db_session) -> None:
    body = "Документ описывает IdeaVault Flow и связанные темы."
    rag_repo.add_document_with_chunks(
        db_session,
        project="prompt-course",
        source_type="local",
        source_uri="local:nl-znaesh.md",
        title="nl-znaesh.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    hits = search_rag_chunks(
        db_session,
        "Что знаешь про IdeaVault Flow",
        current_project="prompt-course",
        limit=5,
    )
    assert hits


def test_rag_simple_literal_IdeaVault_Flow_still_works(db_session) -> None:
    body = "Только маркер SimpleIvfLiteral99 и строка IdeaVault Flow здесь."
    rag_repo.add_document_with_chunks(
        db_session,
        project="studycase",
        source_type="local",
        source_uri="local:simple-ivf.md",
        title="simple-ivf.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    hits = search_rag_chunks(
        db_session,
        "IdeaVault Flow",
        current_project="studycase",
        limit=5,
    )
    assert hits
    assert any("SimpleIvfLiteral99" in (h.get("text") or "") for h in hits)


def test_rag_search_hyphenated_query_matches_spaced_product_name(db_session) -> None:
    """Запрос с дефисом находит чанк с двумя словами (как в UI: ideavault-flow vs IdeaVault Flow)."""
    body = "Коротко: продукт IdeaVault Flow в рамках курса."
    rag_repo.add_document_with_chunks(
        db_session,
        project="prompt-course",
        source_type="local",
        source_uri="local:readme.md",
        title="README.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    hits = search_rag_chunks(db_session, "ideavault-flow", current_project="prompt-course", limit=5)
    assert hits
    assert hits[0]["title"] == "README.md"


def test_forced_project_rag_overrides_null_session(db_session) -> None:
    """Web UI: forced_project из URL даёт scope RAG, даже если sessions.current_project = NULL."""
    from app.repositories import sessions_repo
    from app.services.bot_dialog_service import process_incoming_text

    body = "ForcedUiRagDesyncToken уникальный маркер для теста."
    rag_repo.add_document_with_chunks(
        db_session,
        project="prompt-course",
        source_type="local",
        source_uri="local:desync.md",
        title="desync.md",
        body=body,
        chunk_texts=chunking.chunk_text(body),
    )
    uid = "ui-desync-user"
    sessions_repo.upsert_chat_mode(db_session, uid, "rag")
    sessions_repo.upsert_current_project(db_session, uid, None)

    reply = process_incoming_text(
        db_session,
        uid,
        "ForcedUiRagDesyncToken",
        forced_project="prompt-course",
    )
    assert "ничего не найдено" not in reply.lower()
    assert "ForcedUiRagDesyncToken" in reply


def test_answer_rag_honest_empty(db_session) -> None:
    out = rag_answer_service.answer_rag(
        db_session,
        question="zzznomatchxyz123",
        current_project=None,
        include_item_hints=False,
    )
    assert "ничего не найдено" in out.lower()
