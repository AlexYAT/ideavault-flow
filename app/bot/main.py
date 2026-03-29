"""
Telegram bot entrypoint.

Run: ``python -m app.bot.main`` from project root (with ``.env`` loaded).
"""

import logging
import sys

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.handlers import commands, messages, photos, project_picker, rag_commands, voice
from app.config import settings
from app.db.base import init_db
from app.logging import setup_logging

logger = logging.getLogger(__name__)

_DEFAULT_BOT_COMMANDS: list[BotCommand] = [
    BotCommand("start", "Начало работы"),
    BotCommand("project", "Выбрать проект"),
    BotCommand("set", "Установить проект: /set <имя>"),
    BotCommand("clear", "Сбросить проект"),
    BotCommand("mode", "Режим работы (vault/rag)"),
    BotCommand("index", "Индексировать базу знаний"),
    BotCommand("stats", "Статистика"),
    BotCommand("resetchat", "Сбросить диалог"),
]


async def _post_init_set_commands(application: Application) -> None:
    """Register commands in Telegram client menu (blue / button)."""
    await application.bot.set_my_commands(_DEFAULT_BOT_COMMANDS)


def build_application() -> Application:
    """Register command, text, and voice handlers (long polling)."""
    token = settings.telegram_bot_token.strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing or empty. Set it in .env or the environment.",
        )
    app = Application.builder().token(token).post_init(_post_init_set_commands).build()
    app.add_handler(CommandHandler("start", commands.cmd_start))
    app.add_handler(CommandHandler("set", commands.cmd_set))
    app.add_handler(CommandHandler("current", commands.cmd_current))
    app.add_handler(CommandHandler("projects", commands.cmd_projects))
    app.add_handler(CommandHandler("project", project_picker.cmd_project))
    app.add_handler(project_picker.project_callback_handler())
    app.add_handler(CommandHandler("clear", commands.cmd_clear))
    app.add_handler(CommandHandler("resetchat", commands.cmd_resetchat))
    app.add_handler(CommandHandler("review", commands.cmd_review))
    app.add_handler(CommandHandler("next", commands.cmd_next))
    app.add_handler(CommandHandler("mode", rag_commands.cmd_mode))
    app.add_handler(CommandHandler("rag_bind", rag_commands.cmd_rag_bind))
    app.add_handler(CommandHandler("rag_paths", rag_commands.cmd_rag_paths))
    app.add_handler(CommandHandler("index", rag_commands.cmd_index))
    app.add_handler(CommandHandler("stats", rag_commands.cmd_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages.on_text))
    app.add_handler(MessageHandler(filters.VOICE, voice.on_voice))
    app.add_handler(MessageHandler(filters.PHOTO, photos.on_photo))
    return app


def main() -> None:
    """Initialize logging/DB, build app, run polling."""
    setup_logging()
    logger.info("IdeaVault Flow Telegram bot starting (polling)...")
    init_db()
    try:
        application = build_application()
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    logger.info("Bot logged in; listening for updates.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
