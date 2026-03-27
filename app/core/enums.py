"""Domain enumerations for items, capture sources, and session state."""

from enum import StrEnum


class ItemStatus(StrEnum):
    """Lifecycle state of a captured item."""

    NEW = "new"
    INBOX = "inbox"
    # TODO: ACTIVE, DONE, ARCHIVED as the product matures


class ItemPriority(StrEnum):
    """Rough prioritization for review ordering."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class CaptureSource(StrEnum):
    """Where the raw payload originated."""

    TELEGRAM_TEXT = "telegram_text"
    TELEGRAM_PHOTO = "telegram_photo"
    TELEGRAM_VOICE = "telegram_voice"
    API = "api"
    # TODO: extend for other channels


class ChatMode(StrEnum):
    """High-level user interaction mode."""

    CAPTURE = "capture"
    CHAT = "chat"
