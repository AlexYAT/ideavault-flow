"""Review / ask endpoint contracts (MVP stub, no LLM)."""

from pydantic import BaseModel, Field

from app.schemas.search import SearchHit


class ReviewAskRequest(BaseModel):
    """User question and optional project scope for retrieval."""

    user_id: str = Field(..., description="Logical user key (reserved for later auth)")
    message: str = Field(..., min_length=1, description="Query text for FTS retrieval")
    current_project: str | None = Field(
        None,
        description="If set, search this project plus items with NULL project",
    )


class ReviewAskResponse(BaseModel):
    """Stub assistant reply with cited sources and follow-ups."""

    answer: str
    sources: list[SearchHit]
    next_steps: list[str]
