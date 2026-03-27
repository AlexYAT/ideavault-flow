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
  db/  repositories/  services/  schemas/  utils/ (fts_query, query_normalize)
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

## Инициализация базы

```powershell
python scripts/init_db.py
```

При первом запуске **uvicorn** схема создаётся через `lifespan`.

## Запуск FastAPI

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Документация: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) — удобнее, чем `curl` в PowerShell.

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
| `+ текст` | Заметка в SQLite (`source=telegram`) |
| Обычный текст | Поиск через `review_ask_stub` + форматированный ответ |

### Пример сценария в Telegram

1. `/set prompt-course` — область поиска: проект `prompt-course` и глобальные заметки (без проекта).
2. `+ идея для MVP` — сохраняется с текущим проектом.
3. `что у меня по MVP?` — ответ по FTS с блоками «Источники» и «Дальше».

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
