"""Item-related API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    """Payload for creating an item via API."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "Зафиксировать MVP на две недели",
                    "project": "demo-course",
                    "source": "api",
                }
            ]
        },
    )

    text: str = Field(..., min_length=1, description="Note body stored in FTS index")
    project: str | None = Field(None, description="Optional project bucket")
    source: str = Field("api", description="Origin tag, e.g. api / telegram")
    priority: str = Field("normal", description="low | normal | high")
    status: str = Field("new", description="Lifecycle flag (MVP)")
    raw_payload_ref: str | None = Field(None, description="Optional external reference id")


class ItemRead(BaseModel):
    """Item returned from API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    project: str | None
    status: str
    priority: str
    source: str
    raw_payload_ref: str | None
    created_at: datetime
