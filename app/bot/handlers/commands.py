"""Slash commands: /set, /current, /projects, /clear, /next, /review."""

from telegram import Update
from telegram.ext import ContextTypes

# TODO: inject DB session per update; map chat/user id to sessions_repo


async def cmd_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/set <project>` — set current_project. TODO: parse args, persist."""
    _ = context
    await update.effective_message.reply_text("TODO: /set <project>")


async def cmd_current(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/current` — show active project."""
    _ = context
    await update.effective_message.reply_text("TODO: /current")


async def cmd_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/projects` — list known projects."""
    _ = context
    await update.effective_message.reply_text("TODO: /projects")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/clear` — unset current project."""
    _ = context
    await update.effective_message.reply_text("TODO: /clear")


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/next` — suggest next steps."""
    _ = context
    await update.effective_message.reply_text("TODO: /next")


async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/review` — start review / RAG flow."""
    _ = context
    await update.effective_message.reply_text("TODO: /review")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/start` — onboarding."""
    _ = context
    await update.effective_message.reply_text(
        "IdeaVault Flow bot (skeleton). Use +prefix to capture, or chat for RAG."
    )
