"""Telegram slash commands."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.services import project_service

logger = logging.getLogger(__name__)

_START_HELP = """\
Привет! IdeaVault Flow — заметки и поиск по базе.

Команды:
/set <проект> — текущий проект (область поиска)
/current — какой проект выбран
/projects — список проектов из заметок
/clear — сбросить проект

+ текст — сохранить заметку
Обычный текст — поиск по vault (как review)
"""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send short help for new users."""
    _ = context
    await update.effective_message.reply_text(_START_HELP)


async def cmd_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Persist ``current_project`` from ``/set <name>``."""
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    name = " ".join(context.args).strip()
    if not name:
        await update.effective_message.reply_text(
            "Укажите имя проекта: /set my-project",
        )
        return
    with bot_session() as db:
        project_service.set_current_project(db, uid, name)
    logger.info("user=%s set project=%s", uid, name)
    await update.effective_message.reply_text(f"Текущий проект: «{name}».")


async def cmd_current(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show active project or none."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
    if current is None:
        await update.effective_message.reply_text("Проект не выбран (глобальная область).")
    else:
        await update.effective_message.reply_text(f"Текущий проект: «{current}».")


async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List distinct projects from items."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        names = project_service.list_distinct_projects(db)
    if not names:
        await update.effective_message.reply_text(
            "Пока нет проектов в заметках. Сохраните заметку с проектом через API или уточним позже.",
        )
    else:
        await update.effective_message.reply_text("Проекты:\n" + "\n".join(f"• {n}" for n in names))


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear ``current_project``."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        project_service.clear_current_project(db, uid)
    logger.info("user=%s cleared project", uid)
    await update.effective_message.reply_text("Проект сброшен. Область поиска — все заметки.")
