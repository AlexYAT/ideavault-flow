"""CRUD-ish access to captured items."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.repositories import items_repo
from app.schemas.item import ItemCreate, ItemRead

router = APIRouter()

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 500


@router.get("/items", response_model=list[ItemRead])
def list_items(
    project: str | None = None,
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    """List recent items (``created_at`` desc), optional filter by project."""
    rows = items_repo.list_items(db, project=project, limit=limit)
    return [ItemRead.model_validate(r) for r in rows]


@router.post("/items", response_model=ItemRead)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> ItemRead:
    """Create an item; ``created_at`` defaults in the database."""
    row = items_repo.create_item(
        db,
        text=payload.text,
        project=payload.project,
        status=payload.status,
        priority=payload.priority,
        source=payload.source,
        raw_payload_ref=payload.raw_payload_ref,
    )
    return ItemRead.model_validate(row)
