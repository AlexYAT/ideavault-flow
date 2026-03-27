"""Text, photo, and voice message dispatch."""

from telegram import Update
from telegram.ext import ContextTypes

# TODO: download voice, STT, caption merge; call capture_service vs chat_service


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route plaintext: capture (+) vs chat."""
    _ = context
    text = update.effective_message.text or ""
    await update.effective_message.reply_text(f"TODO: handle text ({text[:40]}…)")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo + optional caption."""
    _ = context
    await update.effective_message.reply_text("TODO: photo + caption capture")


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice note → transcript → capture/chat."""
    _ = context
    await update.effective_message.reply_text("TODO: voice → transcript")
