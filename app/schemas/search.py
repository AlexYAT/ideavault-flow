"""Search-oriented Pydantic models."""

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """Single full-text hit aligned with stored items (subset of columns)."""

    id: int
    text: str
    project: str | None = None


class SearchOut(BaseModel):
    """Response body for GET /api/search."""

    hits: list[SearchHit] = Field(default_factory=list, description="Matching items")
