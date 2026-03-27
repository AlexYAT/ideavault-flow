"""Search-oriented Pydantic models."""

from pydantic import BaseModel, ConfigDict, Field


class SearchHit(BaseModel):
    """Single full-text hit aligned with stored items (subset of columns)."""

    id: int = Field(..., description="`items.id`")
    text: str = Field(..., description="Matched note body")
    project: str | None = Field(None, description="Project column if set")


class SearchOut(BaseModel):
    """Legacy shape (hits); prefer :class:`SearchItemsOut` for new clients."""

    hits: list[SearchHit] = Field(default_factory=list, description="Matching items")


class SearchItemsOut(BaseModel):
    """GET /search response: echoes ``query`` and returns hits as ``items``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "mvp",
                    "items": [{"id": 1, "text": "MVP scope draft", "project": "demo"}],
                }
            ]
        },
    )

    query: str = Field(..., description="Original search string")
    items: list[SearchHit] = Field(default_factory=list, description="Matching notes")
