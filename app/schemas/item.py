"""Item-related API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    """Payload for creating an item via API."""

    text: str = Field(..., min_length=1)
    project: str | None = None
    source: str = "api"
    priority: str = "normal"
    status: str = "new"
    raw_payload_ref: str | None = None


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
