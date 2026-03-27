"""Telegram slash commands."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.services import (
    chat_history_service,
    next_actions_service,
    project_service,
    project_snapshot_service,
)

logger = logging.getLogger(__name__)

_START_HELP = """\
Привет! IdeaVault Flow — заметки, поиск и RAG по материалам курса/проекта.

Команды:
/set <проект> — текущий проект (область поиска)
/current — какой проект выбран
/projects — список проектов из заметок
/project — выбрать существующий проект кнопками
/clear — сбросить проект
/resetchat — сбросить контекст чата (история для текущего проекта и режима)
/review — снимок заметок по текущей области
/next — следующие шаги (эвристики по текстам)

Режимы:
/mode — текущий режим (vault | rag)
/mode vault — обычный текст = поиск по заметкам (как раньше)
/mode rag — вопросы по базе знаний (файлы data/knowledge/ + GitHub)

RAG / учёба:
/rag_bind owner/repo [ветка] — привязать репозиторий к **текущему** проекту
/rag_paths [файлы.md …] — whitelist .md для GitHub (без аргументов — показать)
/index — переиндексировать локальные файлы и GitHub

+ текст — сохранить заметку
Голосовое — распознавание (нужен OPENAI_API_KEY), дальше как обычный текст
В режиме vault: обычный текст — поиск по vault
В режиме rag: обычный текст — вопрос по RAG (с источниками)

/stats — заметки + документы RAG

Подробнее см. README (раздел RAG).
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
        reset = project_service.set_current_project(db, uid, name)
    logger.info("user=%s set project=%s", uid, name)
    extra = "\n\nКонтекст чата сброшен (новая сессия для этого проекта и режима)." if reset else ""
    await update.effective_message.reply_text(f"Текущий проект: «{name}».{extra}")


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
        reset = project_service.clear_current_project(db, uid)
    logger.info("user=%s cleared project", uid)
    extra = "\nКонтекст чата сброшен (глобальная область)." if reset else ""
    await update.effective_message.reply_text(
        f"Проект сброшен. Область поиска — все заметки.{extra}",
    )


async def cmd_resetchat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open a new :class:`~app.db.tables.ChatThread` for current project + mode (history not mixed)."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        chat_history_service.start_fresh_thread(db, uid)
    await update.effective_message.reply_text(
        "Контекст чата сброшен. Старые сообщения остаются в БД, но новый диалог начат с чистого листа.",
    )


async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Structured snapshot for current or global scope."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
        text = project_snapshot_service.format_project_review(db, current_project=current)
    await update.effective_message.reply_text(text)


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deterministic next-action list from saved notes."""
    _ = context
    uid = telegram_user_id(update)
    if uid is None:
        await update.effective_message.reply_text("Не удалось определить пользователя.")
        return
    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
        text = next_actions_service.format_next_message(db, current_project=current)
    await update.effective_message.reply_text(text)
