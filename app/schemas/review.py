"""Review / ask endpoint contracts (MVP stub, no LLM)."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.search import SearchHit


class ReviewAskRequest(BaseModel):
    """User question and optional project scope for retrieval."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"user_id": "1", "message": "что у меня по MVP?", "current_project": "demo"},
            ]
        },
    )

    user_id: str = Field(..., description="Logical user key (reserved for later auth)")
    message: str = Field(..., min_length=1, description="Query text for FTS retrieval")
    current_project: str | None = Field(
        None,
        description="If set, search this project plus items with NULL project",
    )


class ReviewAskResponse(BaseModel):
    """Stub assistant reply with cited sources and follow-ups."""

    answer: str = Field(..., description="Formatted answer (deterministic ± LLM)")
    sources: list[SearchHit] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list, description="Suggested follow-up prompts")


class ReviewSnapshotResponse(BaseModel):
    """GET /review snapshot (same text as bot command ``/review``)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "project": "demo",
                    "review": "Фокус: проект «demo»\nВсего записей в области: 2\n...",
                }
            ]
        },
    )

    project: str | None = Field(None, description="Scoped project, or null for all notes")
    review: str = Field(..., description="Formatted snapshot body")
