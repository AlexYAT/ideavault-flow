"""LLM layer: prompts, availability, graceful fallback (no live OpenAI calls)."""

import logging
from unittest.mock import MagicMock

from app.integrations.llm_prompts import (
    SYSTEM_CHAT,
    SYSTEM_CHAT_NO_SOURCES,
    SYSTEM_NEXT,
    SYSTEM_RAG_NO_HITS,
    SYSTEM_REVIEW,
    build_chat_user_prompt,
    build_next_user_prompt,
    build_review_user_prompt,
    format_notes_block,
)
from app.integrations.llm_client import OpenAIChatClient
from app.config import Settings
from app.schemas.search import SearchHit
from app.services.llm_enhancement import try_enhance_chat, try_enhance_rag_answer


def test_format_notes_block_truncates_and_includes_id() -> None:
    long = "x" * 500
    block = format_notes_block(
        [SearchHit(id=7, text=long, project="p")],
        max_items=3,
        max_chars_per_note=50,
    )
    assert "id 7" in block
    assert "проект: p" in block
    assert len(block) < len(long)


def test_system_chat_bans_soft_phrases_and_limits_format() -> None:
    assert "В заметках указано" in SYSTEM_CHAT
    assert "Однако" in SYSTEM_CHAT
    assert "В целом" in SYSTEM_CHAT
    assert "трёх" in SYSTEM_CHAT or "трех" in SYSTEM_CHAT


def test_system_review_fixes_three_sections() -> None:
    assert "Фокус:" in SYSTEM_REVIEW
    assert "Темы:" in SYSTEM_REVIEW
    assert "Пробелы:" in SYSTEM_REVIEW


def test_system_next_requires_numbered_list_only() -> None:
    assert "нумерованный" in SYSTEM_NEXT
    assert "3–5" in SYSTEM_NEXT or "3-5" in SYSTEM_NEXT


def test_build_chat_prompt_contains_question_and_scope() -> None:
    hits = [SearchHit(id=1, text="note a", project="demo")]
    u = build_chat_user_prompt("что по MVP?", "demo", hits)
    assert "что по MVP" in u
    assert "demo" in u
    assert "note a" in u
    assert "суть" in u or "system" in u


def test_build_review_prompt_lists_snippets_and_gaps() -> None:
    u = build_review_user_prompt(
        "Фокус: проект «X»",
        3,
        ["one", "two"],
        ["gap1"],
    )
    assert "Фокус" in u
    assert "one" in u
    assert "gap1" in u
    assert "Темы:" in u
    assert "Пробелы:" in u


def test_build_next_prompt_includes_heuristics() -> None:
    u = build_next_user_prompt(
        "course",
        ["line1"],
        ["step a"],
    )
    assert "line1" in u
    assert "step a" in u
    assert "нумерован" in u or "1." in u


def test_try_enhance_chat_calls_llm_when_enabled_and_no_sources(monkeypatch) -> None:
    """При включённом LLM пустой retrieval не даёт llm_skipped — вызывается complete (no_sources)."""
    mock_client = MagicMock()
    mock_client.model_name = "gpt-4o-mini"
    mock_client.complete = MagicMock(return_value=("краткий ответ без заметок", None))
    monkeypatch.setattr(
        "app.services.llm_enhancement.resolve_llm_client",
        lambda _settings: (mock_client, None),
    )
    s = Settings(llm_enabled=True, openai_api_key="sk-test")
    out = try_enhance_chat(
        s,
        message="hi",
        current_project=None,
        sources=[],
    )
    assert out == "краткий ответ без заметок"
    mock_client.complete.assert_called_once()
    call_kw = mock_client.complete.call_args.kwargs
    assert call_kw["system"] == SYSTEM_CHAT_NO_SOURCES


def test_try_enhance_chat_no_sources_disabled_skips_llm(caplog) -> None:
    """LLM выключен — resolve вернёт skip, complete не вызывается."""
    import logging

    s = Settings(llm_enabled=False, openai_api_key="")
    with caplog.at_level(logging.INFO):
        out = try_enhance_chat(
            s,
            message="hi",
            current_project=None,
            sources=[],
        )
    assert out is None
    assert "llm_skipped" in caplog.text
    assert "disabled" in caplog.text


def test_try_enhance_rag_calls_llm_when_no_chunks(monkeypatch) -> None:
    mock_client = MagicMock()
    mock_client.model_name = "gpt-4o-mini"
    mock_client.complete = MagicMock(return_value=("нет совпадений в RAG", None))
    monkeypatch.setattr(
        "app.services.llm_enhancement.resolve_llm_client",
        lambda _settings: (mock_client, None),
    )
    s = Settings(llm_enabled=True, openai_api_key="sk-test")
    out = try_enhance_rag_answer(
        s,
        question="что?",
        current_project="p1",
        chunks=[],
    )
    assert out == "нет совпадений в RAG"
    assert mock_client.complete.call_args.kwargs["system"] == SYSTEM_RAG_NO_HITS


def test_try_enhance_rag_skipped_when_llm_disabled() -> None:
    s = Settings(llm_enabled=False, openai_api_key="")
    out = try_enhance_rag_answer(
        s,
        question="q",
        current_project=None,
        chunks=[],
    )
    assert out is None


def test_try_enhance_chat_skips_when_disabled() -> None:
    s = Settings(llm_enabled=False)
    out = try_enhance_chat(
        s,
        message="hi",
        current_project=None,
        sources=[SearchHit(id=1, text="x", project=None)],
    )
    assert out is None


def test_try_enhance_chat_logs_skipped_when_disabled(caplog) -> None:
    s = Settings(llm_enabled=False)
    with caplog.at_level(logging.INFO):
        try_enhance_chat(
            s,
            message="hi",
            current_project="proj-a",
            sources=[SearchHit(id=1, text="x", project="proj-a")],
        )
    assert "llm_skipped" in caplog.text
    assert "disabled" in caplog.text


def test_try_enhance_chat_fallback_when_complete_fails(monkeypatch, caplog) -> None:
    mock_client = MagicMock()
    mock_client.model_name = "gpt-4o-mini"
    mock_client.complete = MagicMock(return_value=(None, "timeout"))
    monkeypatch.setattr(
        "app.services.llm_enhancement.resolve_llm_client",
        lambda _settings: (mock_client, None),
    )
    s = Settings(llm_enabled=True, openai_api_key="sk-x")
    with caplog.at_level(logging.INFO):
        out = try_enhance_chat(
            s,
            message="q",
            current_project="p",
            sources=[SearchHit(id=1, text="a", project="p")],
        )
    assert out is None
    assert "llm_fallback_used" in caplog.text
    assert "timeout" in caplog.text


def test_openai_client_from_settings_returns_none_when_disabled(monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.delenv("LLM_ENABLED", raising=False)
    get_settings.cache_clear()
    s = Settings(
        llm_enabled=False,
        openai_api_key="sk-test",
    )
    assert OpenAIChatClient.from_settings(s) is None
    get_settings.cache_clear()


def test_openai_client_from_settings_returns_none_when_no_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = Settings(llm_enabled=True, openai_api_key="")
    assert OpenAIChatClient.from_settings(s) is None


def test_chat_falls_back_to_deterministic_when_enhancement_returns_none(
    db_session,
    monkeypatch,
) -> None:
    from app.repositories import items_repo
    from app.services import chat_service

    monkeypatch.setattr(
        "app.services.llm_enhancement.try_enhance_chat",
        lambda *_a, **_k: None,
    )
    items_repo.create_item(
        db_session,
        text="only seed alpha",
        project="d",
        status="new",
        priority="normal",
        source="api",
    )
    out = chat_service.answer_text_query(
        db_session,
        "1",
        "only seed alpha",
        current_project="d",
    )
    assert "Нашёл" in out or "релевант" in out.lower()


def test_openai_client_builds_when_enabled_and_key(monkeypatch) -> None:
    s = Settings(llm_enabled=True, openai_api_key="sk-x", openai_model="gpt-4o-mini", llm_timeout_seconds=10.0)
    c = OpenAIChatClient.from_settings(s)
    assert c is not None
