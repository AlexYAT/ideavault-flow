# IdeaVault Flow (MVP backend)

Локальный backend для захвата идей в SQLite, полнотекстового поиска (FTS5) и заглушки review без LLM. Telegram на этом этапе не подключается.

## Возможности

- **FastAPI**: `health`, CRUD-подобный `items`, `search`, список проектов, `review/ask` (stub)
- **SQLite** + таблицы `items`, `sessions` и **FTS5** по полю `text`
- При старте приложения вызывается **`init_db()`** (создание таблиц и FTS)
- Отдельно: `python scripts/init_db.py` — инициализация БД без запуска uvicorn

## Структура папок

```text
app/
  main.py              # FastAPI + lifespan (init_db при старте)
  api/routes/          # HTTP endpoints
  db/                  # engine, таблицы, FTS
  schemas/             # Pydantic
  repositories/        # SQLAlchemy
  services/            # сценарии
  utils/               # в т.ч. fts_query — безопасная подготовка FTS MATCH
scripts/
  init_db.py           # ручная инициализация БД
tests/
data/                  # файл БД по умолчанию (sqlite)
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

Скопируйте `.env.example` в `.env` и при необходимости измените:

| Переменная | Описание |
|------------|----------|
| `DATABASE_URL` | По умолчанию `sqlite:///./data/ideavault.db` |
| `LOG_LEVEL` | Например `INFO` |
| `API_HOST` / `API_PORT` | Для справки (uvicorn задаёт хост/порт в CLI) |

## Инициализация базы

Из корня проекта (с активированным venv):

```powershell
python scripts/init_db.py
```

При первом запуске **uvicorn** схема также создаётся автоматически через `lifespan`.

## Запуск FastAPI

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Тесты

```powershell
pytest
```

## Примеры `curl` (ручная проверка)

Подставьте при необходимости другой хост/порт.

**Health**

```powershell
curl -s http://127.0.0.1:8000/api/health
```

**Создать запись**

```powershell
curl -s -X POST http://127.0.0.1:8000/api/items -H "Content-Type: application/json" -d "{\"text\":\"Идея про MVP\",\"project\":\"demo\",\"priority\":\"high\"}"
```

**Список записей**

```powershell
curl -s "http://127.0.0.1:8000/api/items?limit=20"
```

**Поиск (ответ: JSON с полем `hits`)**

```powershell
curl -s "http://127.0.0.1:8000/api/search?q=MVP"
curl -s "http://127.0.0.1:8000/api/search?q=идея&project=demo"
```

**Уникальные проекты (массив строк, без NULL)**

```powershell
curl -s http://127.0.0.1:8000/api/projects
```

**Review (stub, без LLM)**

```powershell
curl -s -X POST http://127.0.0.1:8000/api/review/ask -H "Content-Type: application/json" -d "{\"user_id\":\"1\",\"message\":\"MVP\",\"current_project\":null}"
```

## Задел по продукту

- Telegram-бот, реальная LLM, Alembic, аутентификация — вне текущего этапа.

## Лицензия

Укажите лицензию при публикации на GitHub.
