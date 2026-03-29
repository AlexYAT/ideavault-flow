# IdeaVault Flow — MVP

**Что это:** локальный **MVP «инбокса идей»** — заметки в **SQLite**, полнотекстовый **FTS5**, опциональный **OpenAI** только поверх уже найденного контекста, **Telegram-бот** (polling) и **JSON API** на **FastAPI**, работающие с **одной и той же БД**.

Назначение: связка **захват → хранение → поиск → обзор и ответы**, **RAG по материалам проекта** (локальные знания в `data/knowledge`, привязка к файлам **GitHub** через raw) и **мультимодальный** `POST /capture` без тяжёлой инфраструктуры.

## Основные возможности

- Заметки с текстом; проект как необязательная «папка»; дедуп по нормализованному тексту в рамках проекта (бот `+`).
- Поиск по `text` через FTS5 и нормализацию запроса (AND → OR → одиночные токены).
- **RAG (MVP):** отдельные таблицы `rag_documents` / `rag_chunks` + FTS5 `rag_chunks_fts`; индексация `data/knowledge/<проект>/` и **raw.githubusercontent.com** по привязке `owner/repo` + whitelist путей.
- Режим бота **`/mode rag`**: вопросы по базе знаний с указанием источников; **`/mode vault`** — прежнее поведение (чат по заметкам).
- Команды бота: обзор `/review`, шаги `/next`, сессия проекта `/set`, **`/resetchat`**, **`/rag_bind`**, **`/rag_paths`**, **`/index`**, **`/stats`** (в т.ч. счётчики RAG).
- **Голос в Telegram:** файл сохраняется в `data/voice/<проект|_global>/`, распознавание через OpenAI **Audio Transcriptions** (нужен `OPENAI_API_KEY`); тот же сценарий, что и для текста (vault / RAG, `+` для заметки).
- **История чата (MVP):** сообщения привязаны к потоку `chat_threads` с ключом *(user, project, mode)*; смена проекта, режима или `/resetchat` открывает новый контекст (старые строки в БД не удаляются).
- Опционально: слой **LLM** для чата, `/review`, `/next` и **vision** для `/capture` (при `LLM_ENABLED` и ключе).
- **HTTP API**: health, stats, items, search, projects, review, capture, **`POST /rag/index`**.

## Архитектура (кратко)

1. **Handlers** (Telegram) и **роуты** (FastAPI) остаются тонкими — только ввод/вывод.
2. **Services** собирают сценарии (поиск, обзор, захват, LLM, **RAG-ответы**).
3. **Repositories** ходят в SQLite через SQLAlchemy.
4. **Модуль `app/rag/`** — chunking, источники (локально + GitHub raw), indexer, retriever; позже можно заменить FTS-поиск в retriever на **ChromaDB** без смены контрактов handlers.
5. **Integrations** — OpenAI (текст + vision), промпты и логи.
6. Схема: `items` + **RAG-таблицы** + `project_registry` (имя, описание, `is_system` для **Null**) + `sessions` (`chat_mode`, …); два FTS-индекса (`items_fts`, `rag_chunks_fts`).

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
| `OPENAI_STT_MODEL`, `STT_TIMEOUT_SECONDS` | Распознавание голосовых в боте (Whisper-совместимый endpoint) |

Подробнее о лимитах поиска, LLM и логировании — в разделах ниже в этом файле.

## Demo Knowledge Base

Проект содержит пример файла:

`data/knowledge/_global/example.md`

После запуска выполните в боте **`/index`**, при желании **`/stats`**, затем **`/mode rag`** и задайте вопрос, например: *«что такое IdeaVault?»*

Роль и сценарии ассистента — в **`IDEA.md`**.

## Запуск API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Интерактивная документация: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (OpenAPI-подсказки и примеры схем).

### Web UI (Jinja2)

Основная точка входа: **[http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)** — дашборд проектов. Типичный поток: **дашборд → карточка проекта** (чат, переиндексация RAG, локальные файлы знаний, GitHub bind), при необходимости — **задачи** и **привязка GitHub** по ссылкам со страницы проекта.

Минимальные страницы без JS-фреймворков (только формы):

- **`/ui`** — дашборд: таблица (задачи, локальные файлы знаний, признаки RAG / GitHub), карточки `project_registry`, открытие проекта, удаление (не для служебного **Null**). При удалении проекта заметки переносятся в **Null** с префиксом `Из удаленного …`.
- **`/ui/project/{имя}`** — карточка проекта: при открытии **текущий проект** веб-сессии (`WEB_UI_USER_ID`) совпадает с этим именем; чат (vault / RAG), кнопка **Переиндексировать RAG** (тот же контур, что `POST /api/rag/index`), блоки локальных файлов и GitHub bind.
- **`/ui/rag`** — привязка GitHub (`?project=…`). Пути проверяются через **raw.githubusercontent.com**; в binding только валидные файлы.
- **`/ui/items`** — список заметок и перенос между проектами.

Прямые URL `/ui/rag`, `/ui/items`, **`/docs`** остаются доступны. Навигация с дашборда и со страницы проекта (верхнее общее меню в шаблоне не используется).

Запуск: `uvicorn app.main:app --reload ...`. Корневой `GET /` в JSON: `"ui": "/ui"`. Сохранён `POST /ui/projects/set` для совместимости.

## Endpoints (дубли с `/api` и без)

| Метод | Путь | Назначение |
|--------|------|------------|
| GET | `/health`, `/api/health` | Liveness: `{"status":"ok"}` |
| GET | `/stats`, `/api/stats` | Сводка vault + RAG: `items_*`, `rag_documents_total`, `rag_chunks_total`, `rag_projects_with_docs` |
| GET | `/items`, `/api/items` | Список заметок (`project`, `limit`) |
| POST | `/items`, `/api/items` | Создать текстовую заметку (JSON) |
| GET | `/search`, `/api/search` | `?q=` → `{"query","items"}` |
| GET | `/projects`, `/api/projects` | Уникальные проекты |
| POST | `/projects/current`, ... | Текущий проект для `user_id` |
| GET | `/review`, `/api/review` | Снимок как в боте (`?project=` опционально) |
| POST | `/review/ask`, ... | Вопрос + retrieval → `answer`, `sources`, `next_steps` |
| POST | `/capture`, `/api/capture` | Multipart: `file` (image), опционально `caption`, `project` |
| POST | `/rag/index`, `/api/rag/index` | JSON `{"project": "имя" \| null}` — переиндексация папки `data/knowledge/…` и GitHub |

### RAG: файлы и GitHub (MVP)

- **Локально:** положите `.md` / `.txt` в `data/knowledge/<имя_проекта>/` (должен совпадать с `/set`) или в **`data/knowledge/_global/`** для знаний без привязки к проекту.
- **GitHub:** `/set course` → `/rag_bind owner/repo main` → опционально `/rag_paths README.md docs/lecture.md` → **`/index`** (или `POST /rag/index` с телом `{"project":"course"}`). Загрузка только по **публичным raw-URL**, без OAuth.
- **Поиск:** при выбранном проекте в RAG учитываются чанки этого проекта **и** глобальные (`project IS NULL`). Без проекта — только глобальные. К ответу могут добавляться 1–2 релевантные **заметки** из vault.

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

**Проект в боте:** создать или задать произвольное имя — **`/set <имя>`** (как и раньше). Переключиться между проектами, которые уже есть в БД (из поля `project` заметок), удобно командой **`/project`**: бот покажет текущий контекст и кнопки; нажатие вызывает ту же логику, что и `/set`, в том числе сброс истории чата при **реальной** смене проекта. Выйти в глобальную область — только **`/clear`**.

### Команды бота (напоминание）

| Команда | Действие |
|---------|----------|
| `/start` | Справка |
| `/set` / `/current` / `/clear` / `/projects` | Проект сессии (при смене проекта контекст чата сбрасывается) |
| `/project` | Только **существующие** проекты из заметок — inline-кнопки; текущий помечен префиксом **•**. Новый проект — **`/set <имя>`**, сброс области — **`/clear`** (кнопок «новый» / «без проекта» нет) |
| `/resetchat` | Новый контекст диалога для текущей пары (проект, режим) |
| `/review` | Снимок области |
| `/next` | Эвристические следующие шаги |
| `+ текст` | Заметка |
| `/mode` | `vault` \| `rag` — режим ответов на свободный текст |
| `/rag_bind`, `/rag_paths`, `/index` | Привязка репозитория, whitelist `.md`, индексация |
| Обычный текст | В `vault` — поиск по заметкам; в `rag` — вопрос по базе знаний |
| Голосовое сообщение | Скачивание → `data/voice/…` → STT → как обычный текст |

## Быстрый сценарий демонстрации (Quick demo flow)

1. Запустить API, открыть **`/ui`** — дашборд проектов; при необходимости — **`/docs`** (`GET /health`, `GET /stats`, поля `rag_*`).
2. Создать проект, открыть карточку; добавить заметки через **`POST /items`** или бот **`+ текст`** в том же проекте.
3. Положить материалы в **`data/knowledge/<проект>/`** и/или настроить GitHub на **`/ui/rag`**; на карточке проекта нажать **Переиндексировать RAG** (или **`/index`** в боте / `POST /rag/index`). Переключить бот или веб-чат в **`rag`** и задать вопрос по базе знаний.
4. Режим **vault**: **`GET /review`** или свободный текст в чате — ответы по заметкам.
5. Опционально: **`POST /capture`** и LLM в `.env`.

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

## Дальнейшее развитие

- **ChromaDB / эмбеддинги** вместо FTS по чанкам (точка расширения — `app/rag/retriever.py`).
- Расширение **STT** (другой провайдер), склейка длинных голосовых, прогресс в чате.
- Alembic, OAuth/JWT, webhook Telegram, отдельное хранилище бинарных вложений.

## Лицензия

Лицензия пока не указана.
