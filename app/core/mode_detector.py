"""Detect capture (+…) vs free-form chat from inbound text."""

from app.core.enums import ChatMode


def detect_mode(text: str) -> ChatMode:
    """
    Return CAPTURE if the message is a capture (leading '+' after trim).

    TODO: support alternate prefixes, slash-commands bypass, empty text edge cases.
    """
    stripped = text.lstrip()
    if stripped.startswith("+"):
        return ChatMode.CAPTURE
    return ChatMode.CHAT


def strip_capture_prefix(text: str) -> str:
    """Remove leading '+' and whitespace for stored item text. TODO: multi-line rules."""
    return text.lstrip().removeprefix("+").lstrip()
