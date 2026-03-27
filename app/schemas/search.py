"""Search-oriented Pydantic models."""

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """Single full-text hit aligned with stored items (subset of columns)."""

    id: int
    text: str
    project: str | None = None


class SearchOut(BaseModel):
    """Legacy shape (hits); prefer :class:`SearchItemsOut` for new clients."""

    hits: list[SearchHit] = Field(default_factory=list, description="Matching items")


class SearchItemsOut(BaseModel):
    """GET /search response: echoes ``query`` and returns hits as ``items``."""

    query: str = Field(..., description="Original search string")
    items: list[SearchHit] = Field(default_factory=list, description="Matching notes")
