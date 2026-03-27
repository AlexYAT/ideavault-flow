"""
Telegram bot entrypoint.

Run: ``python -m app.bot.main`` from project root (with ``.env`` loaded).
"""

import logging
import sys

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.handlers import commands, messages
from app.config import settings
from app.db.base import init_db
from app.logging import setup_logging

logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Register command and text handlers (polling only; no photo/voice in v1)."""
    token = settings.telegram_bot_token.strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing or empty. Set it in .env or the environment.",
        )
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", commands.cmd_start))
    app.add_handler(CommandHandler("set", commands.cmd_set))
    app.add_handler(CommandHandler("current", commands.cmd_current))
    app.add_handler(CommandHandler("projects", commands.cmd_projects))
    app.add_handler(CommandHandler("clear", commands.cmd_clear))
    app.add_handler(CommandHandler("review", commands.cmd_review))
    app.add_handler(CommandHandler("next", commands.cmd_next))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages.on_text))
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
