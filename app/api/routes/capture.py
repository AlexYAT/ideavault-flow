"""Multipart image capture → single item (MVP multimodal)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_api_key
from app.config import get_settings
from app.db.base import get_db
from app.schemas.capture import CaptureOut
from app.services import multimodal_capture_service as mmc

router = APIRouter()


@router.post(
    "/capture",
    response_model=CaptureOut,
    summary="Multimodal capture",
    description=(
        "Multipart: required `file` (image). Optional `caption` and `project`. "
        "Vision needs `LLM_ENABLED` + `OPENAI_API_KEY`; otherwise a text fallback note is stored."
    ),
)
def capture_multimodal(
    file: UploadFile | None = File(default=None, description="Image file (jpeg/png/webp/gif)"),
    caption: str | None = Form(default=None, description="Optional note text / context"),
    project: str | None = Form(default=None, description="Optional project name"),
    db: Session = Depends(get_db),
    _auth: None = Depends(require_api_key),
) -> CaptureOut:
    """
    Save one note from an uploaded image and optional caption.

    Requires an image file. Caption-only requests are rejected here (use POST /items for text).
    """
    cap_norm = mmc.normalize_caption(caption)
    proj_norm = (project or "").strip() or None

    if file is None:
        if not cap_norm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide an image file (`file`). Optional `caption` cannot be the only field.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file (`file`) is required for multimodal capture.",
        )

    raw = file.file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    fname = file.filename or "upload"
    try:
        mime = mmc.validate_image_bytes(
            data=raw,
            declared_type=file.content_type,
            filename=fname,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    settings = get_settings()
    capture_text, _used_vision = mmc.build_capture_text(
        settings,
        image_bytes=raw,
        content_type=mime,
        filename=fname,
        caption=caption,
    )
    item_id = mmc.persist_capture(db, project=proj_norm, capture_text=capture_text)

    return CaptureOut(
        project=proj_norm,
        caption=cap_norm,
        capture=capture_text,
        item_id=item_id,
        status="saved",
    )
