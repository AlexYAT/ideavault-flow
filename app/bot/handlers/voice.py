"""Telegram voice: persist file, STT, reuse text dialog pipeline."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.db import bot_session
from app.bot.handlers.common import telegram_user_id
from app.config import get_settings
from app.integrations import openai_stt
from app.repositories import voice_repo
from app.services import bot_dialog_service, project_service
from app.services.telegram_voice_service import (
    PROJECT_ROOT,
    build_voice_filename,
    download_voice_to_path,
    voice_destination_dir,
)

logger = logging.getLogger(__name__)


def _relative_voice_path(abs_path: Path) -> str:
    try:
        return abs_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return abs_path.resolve().as_posix()


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Voice note: save disk → OpenAI STT → same routing as plain text."""
    uid = telegram_user_id(update)
    if uid is None or update.effective_message is None:
        return
    voice = update.effective_message.voice
    if voice is None:
        return
    settings = get_settings()
    bot = context.bot

    with bot_session() as db:
        current = project_service.get_current_project(db, uid)
        dest_dir = voice_destination_dir(current)
        fname = build_voice_filename(voice)
        dest_abs = dest_dir / fname
        try:
            await download_voice_to_path(bot, voice, dest_abs)
        except Exception as exc:
            logger.warning("voice download failed: %s", exc)
            await update.effective_message.reply_text(
                "Не удалось скачать голосовое сообщение. Попробуйте ещё раз.",
            )
            return

        rel = _relative_voice_path(dest_abs)
        rec = voice_repo.create_recording(
            db,
            user_id=uid,
            project=current,
            storage_path=rel,
            telegram_file_id=voice.file_id,
            telegram_file_unique_id=voice.file_unique_id,
        )

        transcript = await asyncio.to_thread(openai_stt.transcribe_audio_file, dest_abs, settings)
        if transcript:
            voice_repo.finalize_stt(db, rec.id, transcript=transcript, status="ok")
            try:
                item = bot_dialog_service.save_voice_transcript_item(
                    db,
                    transcript=transcript,
                    current_project=current,
                    raw_payload_ref=rel,
                )
            except Exception as exc:
                logger.exception("voice item save failed: %s", exc)
                await update.effective_message.reply_text(
                    f"🎤 Распознано:\n{transcript}\n\n"
                    f"⚠️ Не удалось сохранить заметку ({type(exc).__name__}). "
                    f"Файл: {rel}",
                )
                return
            scope = f"«{current}»" if current else "глобально (без проекта)"
            header = (
                f"🎤 Распознано:\n{transcript}\n\n"
                f"✅ Сохранено как заметка #{item.id} · проект {scope}\n"
                f"Файл: {rel}\n\n"
                f"———\n"
            )
            reply_body = bot_dialog_service.process_incoming_text(
                db, uid, transcript, chat_only=True
            )
            if reply_body:
                await update.effective_message.reply_text(header + reply_body)
            else:
                await update.effective_message.reply_text(header.rstrip())
            return

        voice_repo.finalize_stt(
            db,
            rec.id,
            transcript=None,
            status="failed" if settings.openai_api_key.strip() else "skipped",
        )
        hint = (
            "Не удалось распознать речь (ошибка STT или пустой ответ)."
            if settings.openai_api_key.strip()
            else "Задайте OPENAI_API_KEY в .env для распознавания речи."
        )
        await update.effective_message.reply_text(
            f"{hint}\nФайл сохранён: {rel}",
        )
