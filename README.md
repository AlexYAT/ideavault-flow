# IdeaVault Flow — MVP

**Что это:** локальный **MVP «инбокса идей»** — заметки в **SQLite**, полнотекстовый **FTS5**, опциональный **OpenAI** только поверх уже найденного контекста, **Telegram-бот** (polling) и **JSON API** на **FastAPI**, работающие с **одной и той же БД**.

Цель демонстрации: показать связку **захват → хранение → поиск → краткий обзор / ответ**, плюс **мультимодальный** `POST /capture` (картинка + подпись) без тяжёлой инфраструктуры.

## Основные возможности

- Заметки с текстом; проект как необязательная «папка»; дедуп по нормализованному тексту в рамках проекта (бот `+`).
- Поиск по `text` через FTS5 и нормализацию запроса (AND → OR → одиночные токены).
- Команды бота: обзор `/review`, шаги `/next`, сессия проекта `/set` и т.д.
- Опционально: слой **LLM** для чата, `/review`, `/next` и **vision** для `/capture` (при `LLM_ENABLED` и ключе).
- **HTTP API**: health, список/создание заметок, поиск, проекты, снимок `GET /review`, Q&A `POST /review/ask`, **мультимодальный** `POST /capture`, сводка **`GET /stats`**.

## Архитектура (кратко)

1. **Handlers** (Telegram) и **роуты** (FastAPI) остаются тонкими — только ввод/вывод.
2. **Services** собирают сценарии (поиск, обзор, захват, LLM-постобработка).
3. **Repositories** ходят в SQLite через SQLAlchemy.
4. **Integrations** — HTTP-клиент OpenAI (текст + опционально vision), промпты и безопасные логи.
5. Одна схема `items` + `sessions`; FTS-приставка к содержимому заметок; без отдельного векторного индекса в MVP.

## Быстрый старт (venv)

**Windows (PowerShell):**

```powershell
cd C:\path\to\Project
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:** `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Скопируйте `.env.example` в `.env` и при необходимости задайте токен бота и переменные LLM (см. таблицу ниже).

## Переменные окружения (сжато)

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | SQLite по умолчанию `sqlite:///./data/ideavault.db` |
| `TELEGRAM_BOT_TOKEN` | Для бота |
| `LOG_LEVEL` | Например `INFO` |
| `LLM_ENABLED`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `LLM_*` | Опциональный текстовый LLM и vision для `/capture` |

Подробнее о лимитах поиска, LLM и логировании — в разделах ниже в этом файле.

## Запуск API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Интерактивная документация: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (OpenAPI-подсказки и примеры схем).

## Endpoints (дубли с `/api` и без)

| Метод | Путь | Назначение |
|--------|------|------------|
| GET | `/health`, `/api/health` | Liveness: `{"status":"ok"}` |
| GET | `/stats`, `/api/stats` | Сводка: `items_total`, `projects_total`, `items_with_project` |
| GET | `/items`, `/api/items` | Список заметок (`project`, `limit`) |
| POST | `/items`, `/api/items` | Создать текстовую заметку (JSON) |
| GET | `/search`, `/api/search` | `?q=` → `{"query","items"}` |
| GET | `/projects`, `/api/projects` | Уникальные проекты |
| POST | `/projects/current`, ... | Текущий проект для `user_id` |
| GET | `/review`, `/api/review` | Снимок как в боте (`?project=` опционально) |
| POST | `/review/ask`, ... | Вопрос + retrieval → `answer`, `sources`, `next_steps` |
| POST | `/capture`, `/api/capture` | Multipart: `file` (image), опционально `caption`, `project` |

### Мультимодальный пример (`curl.exe`)

```powershell
curl.exe -s -X POST "http://127.0.0.1:8000/capture" `
  -F "file=@C:\path\to\photo.png" `
  -F "caption=Идея интерфейса" `
  -F "project=demo-course"
```

Ответ: `project`, `caption`, `capture`, `item_id`, `status: "saved"`. Без LLM сохраняется честный текстовый fallback; с ключом — краткое авто-описание изображения при успехе API.

## Запуск Telegram-бота

```powershell
python -m app.bot.main
```

Нужен непустой `TELEGRAM_BOT_TOKEN` в `.env`. Long polling, без webhook.

### Команды бота (напоминание）

| Команда | Действие |
|---------|----------|
| `/start` | Справка |
| `/set` / `/current` / `/clear` / `/projects` | Проект сессии |
| `/review` | Снимок области |
| `/next` | Эвристические следующие шаги |
| `+ текст` | Заметка |
| Обычный текст | Поиск / ответ по заметкам |

## Как показать проект преподавателю (5 шагов)

1. **Запустить API**, открыть **`/docs`**, вызвать **`GET /health`** и **`GET /stats`** (пустая или наполненная БД).
2. **`POST /items`** или бот **`+ заметка`** — создать 2–3 заметки в одном **`project`**.
3. **`GET /search?q=...`** (или бот — свободный текст) — показать FTS.
4. **`GET /review?project=...`** или бот **`/review`** — обзор + «пробелы»; при желании включить LLM в `.env` и показать отличие логов/формулировок.
5. **`POST /capture`** с небольшим png и подписью — мультимодальный захват; при выключенном LLM объяснить fallback; **опционально** — тот же сценарий в боте для одной БД.

## Инициализация БД

```powershell
python scripts/init_db.py
```

При старте uvicorn схема также поднимается в `lifespan`.

## Тесты

```powershell
pytest
```

## Поиск (FTS) и ограничения

Запросы нормализуются (без тяжёлого NLP), затем FTS5: AND по токенам, при пустом результате — OR и объединение одиночных токенов. При «обзорных» формулировках и известном проекте возможен fallback списком последних заметок. **Нет** стемминга/эмбеддингов в MVP.

## Слой LLM и логи

Поиск и выбор заметок **не заменяются** моделью: сначала retrieval, потом короткая генерация **только** по переданным фрагментам. Промпты ужаты под Telegram. Структурированные логи `llm_*` в консоли; `LLM_DEBUG_LOGGING` — дополнительные безопасные поля.

## Ручная проверка API

```powershell
curl.exe -s http://127.0.0.1:8000/api/health
curl.exe -s http://127.0.0.1:8000/api/stats
```

## Что можно улучшить дальше (не обязательно для сдачи)

- Alembic-миграции, OAuth/JWT для API, webhook Telegram, метрики, отдельное хранилище вложений (сейчас в БД только текст заметки после `/capture`).

## Лицензия

Укажите лицензию при публикации репозитория.
