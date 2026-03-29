"""Optional LLM post-processing over retrieval/heuristics (graceful fallback)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.integrations.llm_client import resolve_llm_client
from app.integrations.llm_logging import LLMRequestLogInfo, format_scope, truncate_preview
from app.integrations.llm_prompts import (
    SYSTEM_CHAT,
    SYSTEM_CHAT_NO_SOURCES,
    SYSTEM_NEXT,
    SYSTEM_RAG_GROUNDED,
    SYSTEM_RAG_NO_HITS,
    SYSTEM_REVIEW,
    build_chat_no_sources_user_prompt,
    build_chat_user_prompt,
    build_next_user_prompt,
    build_rag_grounded_user_prompt,
    build_rag_no_hits_user_prompt,
    build_review_user_prompt,
)
from app.schemas.search import SearchHit

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def try_enhance_chat(
    settings: Settings,
    *,
    message: str,
    current_project: str | None,
    sources: list[SearchHit],
) -> str | None:
    """
    LLM над retrieval: при наличии заметок — grounded; при ``llm_enabled`` и пустом retrieval — отдельный no_sources prompt.

    ``None`` → оставить детерминированный ответ (LLM выкл., нет ключа или сбой API).
    """
    scope = format_scope(current_project)
    client, skip = resolve_llm_client(settings)
    notes_count = len(sources)
    if skip:
        logger.info(
            "llm event=llm_skipped mode=chat reason=%s scope=%s notes_count=%d",
            skip,
            scope,
            notes_count,
        )
        return None

    debug = bool(getattr(settings, "llm_debug_logging", False))
    preview = truncate_preview(message) if debug else None

    if not sources:
        logger.info(
            "llm event=llm_call mode=chat context_mode=no_sources scope=%s notes_count=0",
            scope,
        )
        log_info = LLMRequestLogInfo(
            mode="chat",
            scope=scope,
            notes_count=0,
            model=client.model_name,
            query_preview=preview,
            note_ids=(),
        )
        user = build_chat_no_sources_user_prompt(message, current_project)
        out, fail_reason = client.complete(
            system=SYSTEM_CHAT_NO_SOURCES,
            user=user,
            log_info=log_info,
            debug=debug,
        )
        if out is None and fail_reason:
            logger.info(
                "llm event=llm_fallback_used mode=chat context_mode=no_sources scope=%s reason=%s",
                scope,
                fail_reason,
            )
        return out

    logger.info(
        "llm event=llm_call mode=chat context_mode=grounded scope=%s notes_count=%d",
        scope,
        notes_count,
    )
    ids = tuple(s.id for s in sources) if debug else ()
    log_info = LLMRequestLogInfo(
        mode="chat",
        scope=scope,
        notes_count=notes_count,
        model=client.model_name,
        query_preview=preview,
        note_ids=ids,
    )
    user = build_chat_user_prompt(message, current_project, sources)
    out, fail_reason = client.complete(
        system=SYSTEM_CHAT,
        user=user,
        log_info=log_info,
        debug=debug,
    )
    if out is None and fail_reason:
        logger.info(
            "llm event=llm_fallback_used mode=chat scope=%s notes_count=%d reason=%s",
            scope,
            notes_count,
            fail_reason,
        )
    return out


def try_enhance_rag_answer(
    settings: Settings,
    *,
    question: str,
    current_project: str | None,
    chunks: list[dict[str, Any]],
    vault_hint_lines: list[str] | None = None,
) -> str | None:
    """
    LLM для режима RAG: при чанках — grounded; при ``llm_enabled`` и пустом retrieve — no_hits prompt.

    ``None`` — использовать детерминированное форматирование.
    """
    scope = format_scope(current_project)
    client, skip = resolve_llm_client(settings)
    n_chunks = len(chunks)
    if skip:
        logger.info(
            "llm event=llm_skipped mode=rag reason=%s scope=%s chunks=%d",
            skip,
            scope,
            n_chunks,
        )
        return None

    debug = bool(getattr(settings, "llm_debug_logging", False))
    preview = truncate_preview(question) if debug else None

    if not chunks:
        logger.info(
            "llm event=llm_call mode=rag context_mode=no_sources scope=%s chunks=0",
            scope,
        )
        log_info = LLMRequestLogInfo(
            mode="rag",
            scope=scope,
            notes_count=0,
            model=client.model_name,
            query_preview=preview,
            note_ids=(),
        )
        user = build_rag_no_hits_user_prompt(question, current_project)
        out, fail_reason = client.complete(
            system=SYSTEM_RAG_NO_HITS,
            user=user,
            log_info=log_info,
            debug=debug,
        )
        if out is None and fail_reason:
            logger.info(
                "llm event=llm_fallback_used mode=rag context_mode=no_sources scope=%s reason=%s",
                scope,
                fail_reason,
            )
        return out

    logger.info(
        "llm event=llm_call mode=rag context_mode=grounded scope=%s chunks=%d",
        scope,
        n_chunks,
    )
    log_info = LLMRequestLogInfo(
        mode="rag",
        scope=scope,
        notes_count=n_chunks,
        model=client.model_name,
        query_preview=preview,
        note_ids=(),
    )
    user = build_rag_grounded_user_prompt(
        question,
        current_project,
        chunks,
        vault_hint_lines=vault_hint_lines,
    )
    out, fail_reason = client.complete(
        system=SYSTEM_RAG_GROUNDED,
        user=user,
        log_info=log_info,
        debug=debug,
    )
    if out is None and fail_reason:
        logger.info(
            "llm event=llm_fallback_used mode=rag scope=%s chunks=%d reason=%s",
            scope,
            n_chunks,
            fail_reason,
        )
    return out


def try_enhance_review(
    settings: Settings,
    *,
    current_project: str | None,
    focus_line: str,
    n_notes: int,
    snippets: list[str],
    gap_bullets: list[str],
    source_note_ids: tuple[int, ...] = (),
) -> str | None:
    """Concise snapshot from same inputs as deterministic /review."""
    scope = format_scope(current_project)
    client, skip = resolve_llm_client(settings)
    if skip:
        logger.info(
            "llm event=llm_skipped mode=review reason=%s scope=%s notes_count=%d",
            skip,
            scope,
            n_notes,
        )
        return None
    if n_notes < 1:
        logger.info(
            "llm event=llm_skipped mode=review reason=no_sources scope=%s notes_count=0",
            scope,
        )
        return None

    debug = bool(getattr(settings, "llm_debug_logging", False))
    preview = truncate_preview(focus_line) if debug else None
    ids = source_note_ids if debug else ()
    log_info = LLMRequestLogInfo(
        mode="review",
        scope=scope,
        notes_count=n_notes,
        model=client.model_name,
        query_preview=preview,
        note_ids=ids,
    )
    user = build_review_user_prompt(focus_line, n_notes, snippets, gap_bullets)
    out, fail_reason = client.complete(
        system=SYSTEM_REVIEW,
        user=user,
        log_info=log_info,
        debug=debug,
    )
    if out is None and fail_reason:
        logger.info(
            "llm event=llm_fallback_used mode=review scope=%s notes_count=%d reason=%s",
            scope,
            n_notes,
            fail_reason,
        )
    return out


def try_enhance_next(
    settings: Settings,
    *,
    current_project: str | None,
    note_lines: list[str],
    heuristic_steps: list[str],
    source_note_ids: tuple[int, ...] = (),
) -> str | None:
    """Grounded next steps; requires at least one note line."""
    scope = format_scope(current_project)
    client, skip = resolve_llm_client(settings)
    notes_count = len(note_lines)
    if skip:
        logger.info(
            "llm event=llm_skipped mode=next reason=%s scope=%s notes_count=%d",
            skip,
            scope,
            notes_count,
        )
        return None
    if not note_lines:
        logger.info(
            "llm event=llm_skipped mode=next reason=no_sources scope=%s notes_count=0",
            scope,
        )
        return None

    debug = bool(getattr(settings, "llm_debug_logging", False))
    preview = truncate_preview(note_lines[0]) if debug else None
    ids = source_note_ids if debug else ()
    log_info = LLMRequestLogInfo(
        mode="next",
        scope=scope,
        notes_count=notes_count,
        model=client.model_name,
        query_preview=preview,
        note_ids=ids,
    )
    user = build_next_user_prompt(current_project, note_lines, heuristic_steps)
    out, fail_reason = client.complete(
        system=SYSTEM_NEXT,
        user=user,
        log_info=log_info,
        debug=debug,
    )
    if out is None and fail_reason:
        logger.info(
            "llm event=llm_fallback_used mode=next scope=%s notes_count=%d reason=%s",
            scope,
            notes_count,
            fail_reason,
        )
    return out
