"""Voice persistence and STT helpers (no live Telegram / OpenAI)."""

from pathlib import Path

from app.db.tables import VoiceRecording
from app.integrations import openai_stt
from app.repositories import voice_repo
from app.services.telegram_voice_service import build_voice_filename, voice_destination_dir


def test_voice_destination_dir_global(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.telegram_voice_service.VOICE_ROOT", tmp_path / "v")
    d = voice_destination_dir(None)
    assert d == tmp_path / "v" / "_global"
    assert d.is_dir()


def test_build_voice_filename_uses_unique_id() -> None:
    class _V:
        file_unique_id = "abc"
        mime_type = "audio/ogg"

    name = build_voice_filename(_V())  # type: ignore[arg-type]
    assert name.endswith("_abc.oga")


def test_voice_repo_stt_failed_row_and_file_remain(db_session, tmp_path) -> None:
    p = tmp_path / "f.oga"
    p.write_bytes(b"fake")
    rel = p.as_posix()
    row = voice_repo.create_recording(
        db_session,
        user_id="9",
        project="demo",
        storage_path=rel,
        telegram_file_id="fid",
        telegram_file_unique_id="uid",
    )
    voice_repo.finalize_stt(db_session, row.id, transcript=None, status="failed")
    r2 = db_session.get(VoiceRecording, row.id)
    assert r2 is not None
    assert r2.stt_status == "failed"
    assert r2.transcript is None
    assert Path(rel).is_file()


def test_openai_stt_skips_without_api_key(tmp_path) -> None:
    from app.config import Settings

    p = tmp_path / "x.oga"
    p.write_bytes(b"\x00")
    s = Settings(openai_api_key="")
    assert openai_stt.transcribe_audio_file(p, s) is None
