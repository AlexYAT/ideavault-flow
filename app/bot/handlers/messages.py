"""Plain-text messages: capture (+) or vault query."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.core.enums import CaptureSource
from app.core.mode_detector import strip_capture_prefix
from app.services import capture_service, chat_service, project_service

logger = logging.getLogger(__name__)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route ``+`` lines to capture; other text to :func:`chat_service.answer_text_query`."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    raw = (update.effective_message.text or "").strip()
    if not raw:
        return

    if raw.lstrip().startswith("+"):
        with bot_session() as db:
            current = project_service.get_current_project(db, uid)
            cap = capture_service.capture_from_text(
                db,
                raw_text=raw,
                current_project=current,
                source=CaptureSource.TELEGRAM,
            )
        if cap is None:
            await update.effective_message.reply_text(
                "Пустая заметка. Добавьте текст после «+», например: + идея для MVP",
            )
            return
        body = strip_capture_prefix(raw).strip()
        scope = f"«{current}»" if current else "глобально (без проекта)"
        logger.info(
            "user=%s capture item_id=%s duplicate=%s project=%s",
            uid,
            cap.item_id,
            cap.is_duplicate,
            current,
        )
        if cap.is_duplicate:
            msg = (
                f"Такая заметка уже есть (id {cap.item_id}).\n"
                f"{body}\n"
                f"Проект: {scope}"
            )
        else:
            msg = f"Сохранено (id {cap.item_id}).\n{body}\nПроект: {scope}"
        await update.effective_message.reply_text(msg)
        return

    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
        reply = chat_service.answer_text_query(db, uid, raw, current)
    await update.effective_message.reply_text(reply)
