"""
Single entry for user text (Telegram text or STT transcript): capture, vault, RAG + chat history append.

Handlers stay thin; business rules live here.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import CaptureSource, ItemPriority, ItemStatus
from app.core.mode_detector import strip_capture_prefix
from app.db.tables import Item
from app.repositories import items_repo, sessions_repo
from app.repositories.chat_history_repo import append_turn
from app.services import capture_service, chat_service, project_service, rag_answer_service
from app.services.chat_history_service import ensure_chat_thread

_log = logging.getLogger(__name__)

# Текст заметки для входящих фото Telegram (без автоматического описания).
TELEGRAM_PHOTO_ITEM_TEXT = "📷 Получена картинка"


def save_telegram_photo_item(
    db: Session,
    *,
    current_project: str | None,
    raw_payload_ref: str,
) -> Item:
    """Сохранить факт получения фото как заметку (артефакт на диске уже есть)."""
    return items_repo.create_item(
        db,
        text=TELEGRAM_PHOTO_ITEM_TEXT,
        project=current_project,
        status=ItemStatus.NEW.value,
        priority=ItemPriority.NORMAL.value,
        source=CaptureSource.TELEGRAM_PHOTO.value,
        raw_payload_ref=raw_payload_ref,
    )


def save_voice_transcript_item(
    db: Session,
    *,
    transcript: str,
    current_project: str | None,
    raw_payload_ref: str,
) -> Item:
    """Сохранить распознанный голос как заметку (``TELEGRAM_VOICE`` + путь к файлу)."""
    text = transcript.strip()
    if not text:
        raise ValueError("empty transcript")
    return items_repo.create_item(
        db,
        text=text,
        project=current_project,
        status=ItemStatus.NEW.value,
        priority=ItemPriority.NORMAL.value,
        source=CaptureSource.TELEGRAM_VOICE.value,
        raw_payload_ref=raw_payload_ref,
    )


def process_incoming_text(
    db: Session,
    user_id: str,
    raw: str,
    *,
    chat_only: bool = False,
    forced_project: str | None = None,
) -> str:
    """
    Full pipeline for one user text line.

    If ``chat_only`` is True, never treat the line as ``+`` capture (голос уже сохранён отдельным item).

    ``forced_project`` — имя проекта с страницы Web UI (путь ``/ui/project/{name}``): для этого сообщения
    задаёт область vault/RAG независимо от рассинхрона ``sessions.current_project`` (Telegram не передаёт).

    Updates :class:`~app.db.tables.ChatMessage` pairs when not a degenerate empty input.
    """
    text = raw.strip()
    if not text:
        return ""
    if not chat_only and text.lstrip().startswith("+"):
        return _process_capture(db, user_id, raw)
    # Область: forced_project (URL карточки Web UI) → sessions.current_project → None
    if forced_project is not None:
        fp = forced_project.strip()
        current = fp if fp else None
    else:
        current = project_service.get_current_project(db, user_id)
    mode = project_service.get_chat_mode(db, user_id)
    settings = get_settings()
    if settings.rag_retrieval_debug:
        sess = sessions_repo.get_session(db, user_id)
        _log.warning(
            "RAG_E2E_DEBUG TEMP process_incoming_text user_id=%r forced_project=%r "
            "session.current_project=%r effective_current_project=%r chat_mode=%r "
            "session.active_chat_thread_id=%r database_url=%s",
            user_id,
            forced_project,
            sess.current_project if sess else None,
            current,
            mode,
            sess.active_chat_thread_id if sess else None,
            settings.database_url,
        )
    if mode == "rag":
        reply = rag_answer_service.answer_rag(db, question=text, current_project=current)
    else:
        reply = chat_service.answer_text_query(db, user_id, text, current)
    thread = ensure_chat_thread(db, user_id)
    append_turn(db, thread_id=thread.id, user_text=text, assistant_text=reply)
    if settings.rag_retrieval_debug and mode == "rag":
        sess_after = sessions_repo.get_session(db, user_id)
        _log.warning(
            "RAG_E2E_DEBUG TEMP after_rag_reply thread_id=%r session.active_chat_thread_id=%r "
            "reply_has_nothing_found=%s reply_preview=%r",
            thread.id,
            sess_after.active_chat_thread_id if sess_after else None,
            "ничего не найдено" in (reply or "").lower(),
            (reply[:160] + "…") if reply and len(reply) > 160 else (reply or ""),
        )
    return reply


def _process_capture(db: Session, user_id: str, raw: str) -> str:
    thread = ensure_chat_thread(db, user_id)
    current = project_service.get_current_project(db, user_id)
    cap = capture_service.capture_from_text(
        db,
        raw_text=raw,
        current_project=current,
        source=CaptureSource.TELEGRAM,
    )
    if cap is None:
        msg = "Пустая заметка. Добавьте текст после «+», например: + идея для MVP"
        append_turn(db, thread_id=thread.id, user_text=raw.strip(), assistant_text=msg)
        return msg
    body = strip_capture_prefix(raw).strip()
    scope = f"«{current}»" if current else "глобально (без проекта)"
    if cap.is_duplicate:
        msg = (
            f"Такая заметка уже есть (id {cap.item_id}).\n"
            f"{body}\n"
            f"Проект: {scope}"
        )
    else:
        msg = f"Сохранено (id {cap.item_id}).\n{body}\nПроект: {scope}"
    append_turn(db, thread_id=thread.id, user_text=raw.strip(), assistant_text=msg)
    return msg
