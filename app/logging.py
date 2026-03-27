"""Central logging setup."""

import logging
import sys

from app.config import settings


def setup_logging() -> None:
    """Configure root logger once (idempotent-safe for repeated calls)."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    root.setLevel(level)
