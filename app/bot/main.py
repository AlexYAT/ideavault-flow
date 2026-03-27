"""
Telegram bot entrypoint.

Run: `python -m app.bot.main` from project root (with `.env` loaded).
"""

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.handlers import commands, messages
from app.config import settings
from app.db.base import init_db
from app.logging import setup_logging

logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Wire handlers. TODO: error handler, persistence, webhook mode."""
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty; bot will fail to start.")
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", commands.cmd_start))
    app.add_handler(CommandHandler("set", commands.cmd_set))
    app.add_handler(CommandHandler("current", commands.cmd_current))
    app.add_handler(CommandHandler("projects", commands.cmd_projects))
    app.add_handler(CommandHandler("clear", commands.cmd_clear))
    app.add_handler(CommandHandler("next", commands.cmd_next))
    app.add_handler(CommandHandler("review", commands.cmd_review))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages.on_text))
    app.add_handler(MessageHandler(filters.PHOTO, messages.on_photo))
    app.add_handler(MessageHandler(filters.VOICE, messages.on_voice))
    return app


def main() -> None:
    """Start polling loop."""
    setup_logging()
    init_db()
    application = build_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
