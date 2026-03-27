"""Shared helpers for Telegram handlers."""

from telegram import Update


def telegram_user_id(update: Update) -> str | None:
    """Return Telegram user id as string, or ``None`` if missing."""
    user = update.effective_user
    if user is None:
        return None
    return str(user.id)
