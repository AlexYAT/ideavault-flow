"""Multipart image capture API response."""

from typing import Literal

from pydantic import BaseModel, Field


class CaptureOut(BaseModel):
    """Result of POST /capture (image + optional caption)."""

    project: str | None = Field(None, description="Target project, if any")
    caption: str = Field("", description="Normalized user caption (may be empty)")
    capture: str = Field(..., description="Final note body stored in `items.text`")
    item_id: int = Field(..., description="New row id in `items`")
    status: Literal["saved"] = Field("saved", description="Persistence outcome")
