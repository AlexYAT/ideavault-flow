# IdeaVault Flow (MVP backend + Telegram v1)

Локальный backend: SQLite, FTS5, FastAPI и Telegram-бот (polling) с тем же хранилищем.

## Возможности

- **FastAPI**: `health`, `items`, `search`, `projects`, `review/ask` (stub)
- **Telegram v1**: `/start`, `/set`, `/current`, `/projects`, `/clear`, заметки с `+`, обычный текст → поиск/review-заглушка  
  При захвате `+` одинаковый текст в том же проекте (после нормализации: регистр, пробелы) **не вставляется повторно** — бот ответит, что заметка уже есть.
- **SQLite** + таблицы `items`, `sessions`, **FTS5** по полю `text`
- Старт API: `init_db()` в **lifespan**
- Отдельно: `python scripts/init_db.py`

### Поиск (FTS) и ограничения

Запросы в чате и в `/api/search` / `review` проходят **локальную** нормализацию (нижний регистр, пунктуация, отсечение коротких и «слов-паразитов» RU/EN без тяжёлого NLP), затем FTS5: сначала **AND** по ключевым токенам, при пустом результате — **OR**, затем объединение по одному токену. Если FTS ничего не дал, а запрос по эвристике похож на обзор по проекту («какие идеи», «что сохранено», упоминание имени проекта в тексте и т.д.) и область проекта известна (сессия или имя в запросе), показывается **краткий список последних заметок** этого проекта. В ответах источники **дедуплицируются** по нормализованному тексту и проекту. Стемминга, эмбеддингов и синонимов по-прежнему **нет** — разные словоформы могут не совпасть.

## Структура папок

```text
app/
  main.py              # FastAPI
  bot/main.py          # Telegram polling
  bot/handlers/        # тонкие хендлеры → services
  api/routes/
  db/  repositories/  services/  schemas/  utils/
  integrations/        # llm_client, llm_prompts (OpenAI поверх retrieval)
scripts/init_db.py
tests/
data/                  # SQLite по умолчанию
```

## Окружение (venv)

**Windows (PowerShell):**

```powershell
cd C:\path\to\ideavault-flow
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

Скопируйте `.env.example` в `.env`:

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | По умолчанию `sqlite:///./data/ideavault.db` |
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) — **нужен для бота** |
| `LOG_LEVEL` | Например `INFO` |
| `LLM_ENABLED` | `false` по умолчанию; при `true` нужен `OPENAI_API_KEY` |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `OPENAI_MODEL` | Например `gpt-4o-mini` |
| `LLM_TIMEOUT_SECONDS` | Таймаут HTTP к Chat Completions (сек.) |
| `LLM_TEMPERATURE` | Температура выборки модели; по умолчанию **0.2** (ниже — стабильнее и обычно короче) |
| `LLM_MAX_TOKENS` | Максимум токенов в ответе модели; по умолчанию **200** — короче ответы, проще уложиться в лимиты Telegram |
| `LLM_DEBUG_LOGGING` | `false` по умолчанию; при `true` — доп. безопасные поля в логах (см. ниже) |

Для **опирающегося на заметки** режима разумный диапазон **0.1–0.3**: ближе к 0.1 — предсказуемее и суше, к 0.3 — чуть больше вариативности. Значение не задано в `.env` → используется **0.2**.

Для **длины ответа** ориентир **120–220** токенов: меньше — короче и предсказуемее, больше — развёрнутее, но риск выйти за удобный размер сообщения в чате.

**Слой LLM:** поиск и выбор заметок **не меняются** — сначала всегда retrieval/эвристики, затем опционально короткая генерация **только** по переданным фрагментам заметок (обычный текст в боте, при необходимости `/review` и `/next`). Если LLM выключен, нет ключа, ошибка или таймаут — остаётся прежний детерминированный ответ.

Тексты промптов **жёстко ограничены под Telegram**: короткий чат без «воды», для `/review` фиксированные блоки «Фокус / Темы / Пробелы», для `/next` только нумерованный список из 3–5 шагов — чтобы ответы были предсказуемыми и удобно читались в мессенджере.

### Логи LLM в терминале

При `LOG_LEVEL=INFO` и запущенном боте/API в консоль пишутся строки с префиксом `llm ` и полем `event=`:

- `llm_skipped` — LLM не вызывался: `reason=` одно из `disabled`, `no_key`, `no_sources`; есть `mode=` (`chat` / `review` / `next`), `scope=` (имя проекта или `global`), `notes_count`.
- `llm_request_started` / `llm_request_success` / `llm_request_failed` — попытка вызова API: модель, `temperature`, `max_tokens`, задержка `latency_ms`, при успехе `response_chars`; при ошибке `reason=` (`timeout`, `http_error`, `invalid_response`, `unexpected_exception`). **Не логируются** ключ API, полный prompt и полный ответ.
- `llm_fallback_used` — после неудачного запроса включён прежний детерминированный ответ; `reason=` совпадает с причиной сбоя запроса.

`LLM_DEBUG_LOGGING=true` добавляет в строку старта запроса безопасные детали: укороченный `query_preview`, список `note_ids`, `prompt_chars`. Секреты по-прежнему не выводятся.

## Инициализация базы

```powershell
python scripts/init_db.py
```

При первом запуске **uvicorn** схема создаётся через `lifespan`.

## Запуск FastAPI

Точка входа приложения — **`app.main:app`** (роуты подключаются из `app/api/routes/`). Тот же процесс не требуется для бота; API и Telegram запускаются **независимо**.

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Документация: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) — удобнее, чем `curl` в PowerShell.

### Endpoints (MVP JSON)

Каждый маршрут доступен **и с префиксом `/api`**, **и без него** (дубликат для простых клиентов).

| Метод | Путь | Назначение |
|--------|------|------------|
| GET | `/health`, `/api/health` | `{"status": "ok"}` |
| GET | `/items`, `/api/items` | Список заметок (query: `project`, `limit`) |
| POST | `/items`, `/api/items` | Создать заметку (тело см. `/docs`) |
| GET | `/search`, `/api/search` | `?q=...` → `{"query": "...", "items": [...]}` |
| GET | `/projects`, `/api/projects` | Список уникальных проектов |
| POST | `/projects/current`, `/api/projects/current` | «Текущий проект» для `user_id` (как в боте) |
| GET | `/review`, `/api/review` | `?project=...` опционально → `{"project": ..., "review": "..."}` (логика как у `/review` в боте) |
| POST | `/review/ask`, `/api/review/ask` | Вопрос + retrieval (stub-ответ с `sources` / `next_steps`) |

## Запуск Telegram-бота

В `.env` должен быть непустой `TELEGRAM_BOT_TOKEN`. Из корня проекта:

```powershell
python -m app.bot.main
```

Режим **только long polling** (без webhook). Без токена процесс завершится с явным сообщением об ошибке.

### Команды бота

| Команда | Действие |
|---------|----------|
| `/start` | Краткая справка |
| `/set <проект>` | Сохранить текущий проект в `sessions` |
| `/current` | Показать текущий проект или «не выбран» |
| `/projects` | Уникальные проекты из `items` |
| `/clear` | Сбросить текущий проект |
| `/review` | Снимок заметок по области (проект или все) + эвристические «пробелы» |
| `/next` | 3–5 следующих шагов по ключевым словам в заметках (без LLM) |
| `+ текст` | Заметка в SQLite (`source=telegram`) |
| Обычный текст | Поиск через `review_ask_stub` + форматированный ответ |

### Пример сценария в Telegram

1. `/set prompt-course` — область команд `/review` и `/next` привязана к проекту.
2. `+ идея для MVP` и `+ добавить review` — две заметки.
3. `/review` — сводка: фокус, число записей, свежие строки, блок «Пробелы» по простым правилам.
4. `/next` — нумерованный список действий (MVP, идеи, сценарии и т.д., если слова есть в текстах).
5. `что у меня по MVP?` — как раньше: поиск по FTS и подсказки.

Тот же файл БД, что использует FastAPI (при одинаковом `DATABASE_URL`).

## Тесты

```powershell
pytest
```

## Ручная проверка HTTP API

**Windows / PowerShell:** встроенный алиас `curl` ведёт себя иначе, чем `curl.exe`; для UTF-8 и привычного синтаксиса удобнее:

- открыть **Swagger** (`/docs`), или
- `curl.exe` с явными флагами, или
- короткий скрипт на Python (`requests`).

Примеры уже есть в истории проекта; базовые проверки:

```powershell
curl.exe -s http://127.0.0.1:8000/api/health
```

## Задел

- Фото, голос, webhook, LLM, Alembic, auth.

## Лицензия

Укажите лицензию при публикации на GitHub.
