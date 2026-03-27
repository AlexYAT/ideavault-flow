"""
Inline picker for existing project names (Telegram ``callback_data`` length-safe).

Callback payloads use ``project:select:<sha256-hex-prefix>`` and are resolved against
:class:`~app.db.tables.Item` distinct projects (same source as ``/projects``).
"""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

CALLBACK_PREFIX = "project:select:"
# 32 hex chars + prefix stays within Telegram's 64-byte callback_data limit.
_HASH_HEX_LEN = 32


def _digest_prefix(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:_HASH_HEX_LEN]


def callback_data_for_project(name: str) -> str:
    """Build ``callback_data`` for an existing project ``name``."""
    return f"{CALLBACK_PREFIX}{_digest_prefix(name)}"


def button_label(name: str, *, is_current: bool, max_len: int = 58) -> str:
    """
    Visible keyboard label; текущий проект отмечен префиксом «• » (компактно, до ``max_len``).
    """
    text = name.strip() or name
    prefix = "• " if is_current else ""
    budget = max_len - len(prefix)
    if budget < 8:
        budget = 8
    if len(text) > budget:
        text = text[: budget - 1] + "…"
    return f"{prefix}{text}"


def resolve_project_from_callback(db: Session, data: str | None) -> str | None:
    """
    Map ``callback_data`` to a project name present in ``list_distinct_projects``.

    Returns:
        Project name or ``None`` if prefix/hash mismatch or project no longer exists.
    """
    if not data or not data.startswith(CALLBACK_PREFIX):
        return None
    token = data[len(CALLBACK_PREFIX) :]
    if len(token) != _HASH_HEX_LEN or any(c not in "0123456789abcdef" for c in token.lower()):
        return None
    token = token.lower()
    # Local import avoids circular imports at load time.
    from app.services import project_service

    for pname in project_service.list_distinct_projects(db):
        if _digest_prefix(pname) == token:
            return pname
    return None


def picker_message_lines(current: str | None, *, has_projects: bool) -> str:
    """Первая строка — текущий scope; дальше подсказка или приглашение выбрать проект."""
    cur_line = (
        f"📂 Текущий проект: {current}"
        if current
        else "📂 Текущий проект: не выбран"
    )
    if not has_projects:
        return cur_line + "\n\nНет проектов в заметках. Создайте проект: /set <имя>"
    return cur_line + "\n\nВыберите проект:"
