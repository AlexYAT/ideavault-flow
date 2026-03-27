"""Multipart image capture API response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CaptureOut(BaseModel):
    """Result of POST /capture (image + optional caption)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "project": "demo",
                    "caption": "Эскиз экрана",
                    "capture": "Эскиз экрана\n\n[Вложение: изображение «x.png», 1204 байт]",
                    "item_id": 42,
                    "status": "saved",
                }
            ]
        },
    )

    project: str | None = Field(None, description="Target project, if any")
    caption: str = Field("", description="Normalized user caption (may be empty)")
    capture: str = Field(..., description="Final note body stored in `items.text`")
    item_id: int = Field(..., description="New row id in `items`")
    status: Literal["saved"] = Field("saved", description="Persistence outcome")
