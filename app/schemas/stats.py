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
