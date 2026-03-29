"""Telegram photo → item на диске + запись, без чат-pipeline."""

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.enums import CaptureSource
from app.services import bot_dialog_service, project_service
from app.services.telegram_photo_service import pick_largest_photo


def test_pick_largest_photo_by_file_size() -> None:
    a = MagicMock(file_size=100, width=10, height=10, file_unique_id="a")
    b = MagicMock(file_size=5000, width=1, height=1, file_unique_id="b")
    assert pick_largest_photo([a, b]) is b


def test_save_telegram_photo_item_with_project(db_session) -> None:
    project_service.set_current_project(db_session, "u1", "photo-proj")
    cur = project_service.get_current_project(db_session, "u1")
    row = bot_dialog_service.save_telegram_photo_item(
        db_session,
        current_project=cur,
        raw_payload_ref="data/telegram_photos/photo-proj/x.jpg",
    )
    assert row.project == "photo-proj"
    assert row.text == bot_dialog_service.TELEGRAM_PHOTO_ITEM_TEXT
    assert row.source == CaptureSource.TELEGRAM_PHOTO.value
    assert row.raw_payload_ref.endswith(".jpg")


def test_save_telegram_photo_item_global(db_session) -> None:
    row = bot_dialog_service.save_telegram_photo_item(
        db_session,
        current_project=None,
        raw_payload_ref="data/telegram_photos/_global/y.jpg",
    )
    assert row.project is None


def test_on_photo_handler_creates_item(db_session, monkeypatch, tmp_path) -> None:
    """Скачивание + заметка в той же БД, что тест (через подмену bot_session)."""
    from app.bot.handlers import photos
    from app.repositories import items_repo

    @contextmanager
    def _fake_session():
        yield db_session

    monkeypatch.setattr("app.bot.handlers.photos.bot_session", _fake_session)
    monkeypatch.setattr(
        "app.bot.handlers.photos.project_service.get_current_project",
        lambda _db, _uid: "demo",
    )
    monkeypatch.setattr("app.bot.handlers.photos.telegram_user_id", lambda _u: "tg1")

    dest_root = tmp_path / "tp"
    dest_root.mkdir()

    async def _fake_download(bot, photo, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"\xff\xd8\xff")

    monkeypatch.setattr("app.bot.handlers.photos.download_photo_to_path", _fake_download)
    monkeypatch.setattr(
        "app.bot.handlers.photos.photo_destination_dir",
        lambda _c: dest_root,
    )

    chat_called: list[object] = []

    def _no_chat_pipeline(*_a, **_k):
        chat_called.append(True)

    monkeypatch.setattr(
        "app.bot.handlers.photos.bot_dialog_service.process_incoming_text",
        _no_chat_pipeline,
    )

    p_small = MagicMock(
        file_size=100,
        width=1,
        height=1,
        file_unique_id="s",
        file_id="id_small",
    )
    p_big = MagicMock(
        file_size=9000,
        width=2000,
        height=2000,
        file_unique_id="L",
        file_id="id_big",
    )
    msg = MagicMock()
    msg.photo = (p_small, p_big)
    update = MagicMock(effective_message=msg)
    context = MagicMock()
    context.bot = MagicMock()
    reply = AsyncMock()
    msg.reply_text = reply

    asyncio.run(photos.on_photo(update, context))

    reply.assert_awaited_once()
    assert "Создана заметка" in reply.call_args[0][0]
    rows = list(items_repo.list_items(db_session, project="demo", limit=10))
    photo_rows = [r for r in rows if r.source == CaptureSource.TELEGRAM_PHOTO.value]
    assert photo_rows
    assert photo_rows[0].text == bot_dialog_service.TELEGRAM_PHOTO_ITEM_TEXT
    assert not chat_called
