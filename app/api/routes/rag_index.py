"""Trigger RAG reindex (local ``data/knowledge/`` + bound GitHub paths)."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.rag.indexer import reindex_project_scope

router = APIRouter()


class RagIndexRequest(BaseModel):
    """Body for ``POST /rag/index``."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"project": "course-2025"}, {"project": None}]},
    )

    project: str | None = Field(
        None,
        description="Project name whose `data/knowledge/<project>/` + GitHub binding to refresh; omit for `_global`",
    )


@router.post(
    "/rag/index",
    summary="Reindex RAG corpus",
    description=(
        "Deletes existing knowledge documents for the scope, rescans local MD/TXT, "
        "then fetches GitHub raw files when a binding exists."
    ),
)
def rag_reindex(body: RagIndexRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Run :func:`app.rag.indexer.reindex_project_scope` and return counters."""
    return reindex_project_scope(db, project=body.project)
