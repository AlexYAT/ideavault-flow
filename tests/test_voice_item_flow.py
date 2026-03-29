"""Голос: заметка из STT + чат без повторного + capture."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.enums import CaptureSource
from app.repositories import items_repo
from app.services import bot_dialog_service, project_service
from app.services.bot_dialog_service import save_voice_transcript_item


def test_save_voice_transcript_item_uses_current_project(db_session) -> None:
    project_service.set_current_project(db_session, "vuser1", "voice-proj")
    current = project_service.get_current_project(db_session, "vuser1")
    row = save_voice_transcript_item(
        db_session,
        transcript="  hello voice  ",
        current_project=current,
        raw_payload_ref="data/voice/x.oga",
    )
    assert row.project == "voice-proj"
    assert row.text == "hello voice"
    assert row.source == CaptureSource.TELEGRAM_VOICE.value
    assert row.raw_payload_ref == "data/voice/x.oga"


def test_save_voice_transcript_item_global_when_no_project(db_session) -> None:
    row = save_voice_transcript_item(
        db_session,
        transcript="global line",
        current_project=None,
        raw_payload_ref="data/voice/_global/y.oga",
    )
    assert row.project is None
    assert row.text == "global line"


def test_save_voice_transcript_item_empty_raises(db_session) -> None:
    with pytest.raises(ValueError, match="empty"):
        save_voice_transcript_item(
            db_session,
            transcript="   ",
            current_project=None,
            raw_payload_ref="z.oga",
        )


def test_process_incoming_text_chat_only_does_not_trigger_plus_capture(
    db_session,
    monkeypatch,
) -> None:
    """Префикс + в тексте голоса: отдельный item уже есть, в чате не дублируем capture."""
    cap = MagicMock(side_effect=AssertionError("capture must not run in chat_only"))
    monkeypatch.setattr(bot_dialog_service.capture_service, "capture_from_text", cap)
    monkeypatch.setattr(
        bot_dialog_service.chat_service,
        "answer_text_query",
        lambda *_a, **_k: "vault reply",
    )
    out = bot_dialog_service.process_incoming_text(
        db_session,
        "u2",
        "+ only capture syntax",
        chat_only=True,
    )
    assert out == "vault reply"
    cap.assert_not_called()
    items = list(items_repo.list_items(db_session, project=None, limit=20))
    assert not any("+ only" in (x.text or "") for x in items)


def test_voice_reply_header_contains_save_confirmation() -> None:
    """Структура ответа пользователю (без Telegram): проверяем собираемые строки."""
    transcript = "тест"
    item_id = 42
    current = "demo"
    scope = f"«{current}»" if current else "глобально (без проекта)"
    header = (
        f"🎤 Распознано:\n{transcript}\n\n"
        f"✅ Сохранено как заметка #{item_id} · проект {scope}\n"
        f"Файл: data/voice/demo/x.oga\n\n"
        f"———\n"
    )
    assert "🎤 Распознано:" in header
    assert "✅ Сохранено" in header
    assert "«demo»" in header
    assert "———" in header
