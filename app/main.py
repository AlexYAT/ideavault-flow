"""FastAPI application entry."""

from fastapi import FastAPI

from app.api.routes import health, items, projects, review, search
from app.config import settings
from app.db.base import init_db
from app.logging import setup_logging

setup_logging()
init_db()

app = FastAPI(
    title="IdeaVault Flow API",
    description="Review, search, and RAG over captured ideas (MVP skeleton).",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(items.router, prefix="/api", tags=["items"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(review.router, prefix="/api", tags=["review"])


@app.get("/")
def root() -> dict[str, str]:
    """Service identity."""
    return {"service": "ideavault-flow", "docs": "/docs"}
