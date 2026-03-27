# IdeaVault Flow (MVP skeleton)

Мультимодальный ассистент для захватов идей и чата с контекстом из SQLite: Telegram (захват и диалог), FastAPI (просмотр, поиск, RAG-заготовка), SQLite + FTS5 по полю `text`.

## Возможности каркаса

- Таблицы `items` и `sessions`, инициализация через `init_db()`
- Виртуальная таблица `items_fts` (FTS5) и триггеры синхронизации с `items`
- Реальный эндпоинт `GET /api/health`
- Остальное — скелеты с `TODO` для следующей итерации

## Структура папок

```text
app/
  main.py              # FastAPI приложение
  config.py            # Настройки (pydantic-settings)
  logging.py
  api/routes/          # HTTP: health, items, search, projects, review
  bot/                 # Telegram: main + handlers/
  core/                # enums, mode_detector (+ vs chat)
  db/                  # engine, tables, FTS
  models/              # доменные модели (вне ORM) — задел
  schemas/             # Pydantic для API
  repositories/        # запросы к БД
  services/            # сценарии: capture, chat, search, rag, projects, reports
  integrations/        # внешние API — задел
  utils/               # утилиты — задел
tests/                 # pytest
scripts/               # служебные скрипты — задел
data/                  # SQLite файл по умолчанию
reports/               # выгрузки отчётов — задел
```

## Окружение (venv)

**Windows (PowerShell):**

```powershell
cd C:\Work\Edu\Prompt\4\9\Project
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните значения:

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | По умолчанию `sqlite:///./data/ideavault.db` |
| `TELEGRAM_BOT_TOKEN` | Токен бота от BotFather |
| `LOG_LEVEL` | Например `INFO` |
| `API_HOST` / `API_PORT` | Хост и порт uvicorn |

## Запуск FastAPI

Из корня проекта (с активированным venv):

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Документация OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Запуск Telegram-бота

```powershell
python -m app.bot.main
```

Без установленного `TELEGRAM_BOT_TOKEN` процесс не сможет подключиться к Telegram; для проверки API достаточно uvicorn.

## Тесты

```powershell
pytest
```

## Задел по продукту

- **Capture:** сообщения с префиксом `+`, проект из `current_project` или `null`
- **Chat / RAG:** область поиска зависит от наличия текущего проекта (см. `app/services/search_service.py`)
- **Команды бота:** `/set`, `/current`, `/projects`, `/clear`, `/next`, `/review` — заготовки в `app/bot/handlers/`

## Лицензия

Укажите лицензию при публикации на GitHub.
