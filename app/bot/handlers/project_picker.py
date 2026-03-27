"""``/project`` — inline keyboard over existing projects (no create/clear shortcuts)."""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.services import project_picker_service, project_service

logger = logging.getLogger(__name__)


def _build_markup(names: list[str], current: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for name in names:
        is_cur = current == name
        label = project_picker_service.button_label(name, is_current=is_cur)
        cb = project_picker_service.callback_data_for_project(name)
        rows.append([InlineKeyboardButton(label, callback_data=cb)])
    return InlineKeyboardMarkup(rows)


async def cmd_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current project and a keyboard of names from the vault (items)."""
    _ = context
    uid = telegram_user_id(update)
    msg = update.effective_message
    if msg is None:
        return
    if uid is None:
        await msg.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
        names = project_service.list_distinct_projects(db)
    text = project_picker_service.picker_message_lines(current, has_projects=bool(names))
    if not names:
        await msg.reply_text(text)
        return
    await msg.reply_text(text, reply_markup=_build_markup(names, current))


async def on_project_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Apply :func:`~app.services.project_service.set_current_project` for picked name."""
    _ = context
    query = update.callback_query
    if query is None or query.data is None:
        return
    uid = telegram_user_id(update)
    if uid is None:
        await query.answer("Не удалось определить пользователя.", show_alert=True)
        return
    with bot_session() as db:
        name = project_picker_service.resolve_project_from_callback(db, query.data)
        if name is None:
            err = "Проект больше не найден. Обновите список через /project"
            try:
                await query.edit_message_text(text=err)
            except Exception as exc:
                logger.warning("edit after stale callback failed: %s", exc)
                await query.answer(err, show_alert=True)
            else:
                await query.answer()
            return
        reset = project_service.set_current_project(db, uid, name)
    body = (
        f"📂 Проект: {name}\nКонтекст обновлён"
        if reset
        else f"📂 Проект уже активен: {name}"
    )
    try:
        await query.edit_message_text(text=body)
    except Exception as exc:
        logger.warning("edit_message_text failed: %s", exc)
        await query.answer(body, show_alert=True)
    else:
        await query.answer()


def project_callback_handler() -> CallbackQueryHandler:
    """Pattern-bound handler for ``project:select:*``."""
    return CallbackQueryHandler(
        on_project_selected,
        pattern=f"^{project_picker_service.CALLBACK_PREFIX}",
    )
