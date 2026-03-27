"""
Голос в Telegram реализован в :mod:`app.bot.handlers.voice`:

файл сохраняется под ``data/voice/<проект|_global>/``, STT — :mod:`app.integrations.openai_stt`,
транскрипт обрабатывается через :mod:`app.services.bot_dialog_service` (тот же pipeline, что
и обычный текст: vault / RAG, префикс ``+`` для заметок).
"""

