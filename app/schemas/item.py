"""Item-related API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    """Shared item fields."""

    text: str = Field(..., min_length=1)
    project: str | None = None
    status: str = "inbox"
    priority: str = "normal"
    source: str = "api"


class ItemCreate(ItemBase):
    """Payload for creating an item via API. TODO: multimodal attachments."""

    raw_payload_ref: str | None = None


class ItemRead(ItemBase):
    """Item returned from API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_payload_ref: str | None
    created_at: datetime
