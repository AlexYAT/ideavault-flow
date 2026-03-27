"""Central logging setup."""

import logging
import sys

from app.config import settings


def _silence_token_leaking_http_loggers() -> None:
    """
    ``httpx``/``httpcore`` log full request URLs at INFO; Telegram API paths include the bot token.

    Keep them at WARNING so the console does not echo secrets.
    """
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def setup_logging() -> None:
    """Configure root logger once (idempotent-safe for repeated calls)."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        _silence_token_leaking_http_loggers()
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    root.setLevel(level)
    _silence_token_leaking_http_loggers()
