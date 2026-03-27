"""Plain-text messages: capture (+), vault query, or RAG — via :mod:`app.services.bot_dialog_service`."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.services import bot_dialog_service

logger = logging.getLogger(__name__)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delegate one text line to :func:`~app.services.bot_dialog_service.process_incoming_text`."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    raw = (update.effective_message.text or "").strip()
    if not raw:
        return
    with bot_session() as db:
        reply = bot_dialog_service.process_incoming_text(db, uid, raw)
    await update.effective_message.reply_text(reply)
