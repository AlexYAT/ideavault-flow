"""Persist Telegram voice artifacts and STT results."""

from sqlalchemy.orm import Session

from app.db.tables import VoiceRecording


def create_recording(
    db: Session,
    *,
    user_id: str,
    project: str | None,
    storage_path: str,
    telegram_file_id: str,
    telegram_file_unique_id: str,
) -> VoiceRecording:
    row = VoiceRecording(
        user_id=user_id,
        project=project,
        storage_path=storage_path,
        telegram_file_id=telegram_file_id,
        telegram_file_unique_id=telegram_file_unique_id,
        stt_status="pending",
        transcript=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def finalize_stt(
    db: Session,
    recording_id: int,
    *,
    transcript: str | None,
    status: str,
) -> None:
    row = db.get(VoiceRecording, recording_id)
    if row is None:
        return
    row.transcript = transcript
    row.stt_status = status
    db.commit()
