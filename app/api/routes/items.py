"""CRUD-ish access to captured items."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.repositories import items_repo
from app.schemas.item import ItemCreate, ItemRead

router = APIRouter()


@router.get("/items", response_model=list[ItemRead])
def list_items(
    project: str | None = None,
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    """List items; optional project filter. TODO: auth, pagination."""
    rows = items_repo.list_items(db, project=project)
    return [ItemRead.model_validate(r) for r in rows]


@router.post("/items", response_model=ItemRead)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> ItemRead:
    """Create item via API (bypass Telegram). TODO: validation, quotas."""
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
