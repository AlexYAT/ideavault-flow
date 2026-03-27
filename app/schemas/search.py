"""Search and RAG-oriented schemas."""

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """FTS search parameters. TODO: filters, pagination, highlight snippets."""

    q: str = Field(..., min_length=1, description="FTS query string")
    project: str | None = Field(None, description="Scope to project; null = all / global rules in service")


class SearchHit(BaseModel):
    """Single search result row. TODO: bm25 score, snippet."""

    id: int
    text: str
    project: str | None
