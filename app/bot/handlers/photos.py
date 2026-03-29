"""Telegram photo: сохранить файл и заметку без LLM/vision и без чат-pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.services import bot_dialog_service, project_service
from app.services.telegram_photo_service import (
    PROJECT_ROOT,
    build_photo_filename,
    download_photo_to_path,
    photo_destination_dir,
    pick_largest_photo,
)

logger = logging.getLogger(__name__)


def _relative_photo_path(abs_path: Path) -> str:
    try:
        return abs_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return abs_path.resolve().as_posix()


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Фото: диск → item (telegram_photo). Без caption в текст заметки, без чата и vision.
    """
    uid = telegram_user_id(update)
    if uid is None or update.effective_message is None:
        return
    photos = update.effective_message.photo
    if not photos:
        return
    bot = context.bot

    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
        best = pick_largest_photo(list(photos))
        dest_dir = photo_destination_dir(current)
        fname = build_photo_filename(best)
        dest_abs = dest_dir / fname
        try:
            await download_photo_to_path(bot, best, dest_abs)
        except Exception as exc:
            logger.warning("photo download failed: %s", exc)
            await update.effective_message.reply_text(
                "Не удалось сохранить фото. Попробуйте ещё раз.",
            )
            return

        rel = _relative_photo_path(dest_abs)
        try:
            item = bot_dialog_service.save_telegram_photo_item(
                db,
                current_project=current,
                raw_payload_ref=rel,
            )
        except Exception as exc:
            logger.exception("photo item save failed: %s", exc)
            await update.effective_message.reply_text(
                "📷 Файл сохранён, но не удалось создать заметку "
                f"({type(exc).__name__}).\nПуть: {rel}",
            )
            return

        scope = f"«{current}»" if current else "глобально (без проекта)"
        await update.effective_message.reply_text(
            "📷 Картинка сохранена.\n"
            f"✅ Создана заметка #{item.id} в проекте {scope}.\n"
            "Текст заметки можно отредактировать позже (в т.ч. в Web UI).",
        )
