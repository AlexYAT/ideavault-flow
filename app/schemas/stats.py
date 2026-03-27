"""Aggregated vault counters for demos and dashboards."""

from pydantic import BaseModel, ConfigDict, Field


class VaultStatsOut(BaseModel):
    """Lightweight snapshot of note volume (no heavy queries)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items_total": 24,
                    "projects_total": 4,
                    "items_with_project": 20,
                    "rag_documents_total": 3,
                    "rag_chunks_total": 12,
                    "rag_projects_with_docs": 1,
                }
            ]
        },
    )

    items_total: int = Field(..., description="All captured notes in `items`")
    projects_total: int = Field(..., description="Distinct non-null project names")
    items_with_project: int = Field(
        ...,
        description="Notes that have a project set (non-NULL `project` column)",
    )
    rag_documents_total: int = Field(0, description="Ingested knowledge documents (RAG)")
    rag_chunks_total: int = Field(0, description="Searchable RAG chunks (FTS today)")
    rag_projects_with_docs: int = Field(
        0,
        description="Distinct projects that have at least one knowledge document",
    )
