"""FastAPI application entry."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import capture, health, items, projects, review, search, stats
from app.db.base import init_db
from app.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize database schema on application startup."""
    init_db()
    yield


app = FastAPI(
    title="IdeaVault Flow API",
    description=(
        "**MVP:** capture ideas as SQLite notes, search with FTS5, optional OpenAI layer for "
        "grounded answers, Telegram bot + JSON HTTP API sharing one database. "
        "Use `/docs` to try endpoints; multimodal capture is `POST /capture` (multipart image)."
    ),
    version="0.1.0",
    lifespan=lifespan,
    contact={"name": "IdeaVault Flow MVP"},
)

# `/api/...` — основной префикс; дубликаты без префикса — для простого MVP/сдачи заданий.
_API_PREFIX = "/api"
for _router, _tag in (
    (health.router, "health"),
    (stats.router, "stats"),
    (items.router, "items"),
    (search.router, "search"),
    (projects.router, "projects"),
    (review.router, "review"),
    (capture.router, "capture"),
):
    app.include_router(_router, prefix=_API_PREFIX, tags=[_tag])
    app.include_router(_router, prefix="", tags=[_tag])


@app.get(
    "/",
    summary="Service banner",
    description="Identifies the API; open `/docs` for Swagger UI.",
)
def root() -> dict[str, str]:
    """Service identity."""
    return {"service": "ideavault-flow", "docs": "/docs"}
