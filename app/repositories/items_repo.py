"""Persistence for `Item` rows."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import Item


def list_items(db: Session, *, project: str | None = None, limit: int = 100) -> Sequence[Item]:
    """Return recent items, optionally filtered by project. TODO: cursor pagination."""
    stmt = select(Item).order_by(Item.id.desc()).limit(limit)
    if project is not None:
        stmt = stmt.where(Item.project == project)
    return db.scalars(stmt).all()


def get_item(db: Session, item_id: int) -> Item | None:
    """Load a single item by id."""
    return db.get(Item, item_id)


def create_item(
    db: Session,
    *,
    text: str,
    project: str | None,
    status: str,
    priority: str,
    source: str,
    raw_payload_ref: str | None = None,
) -> Item:
    """Insert a new item. TODO: validate enums, attachments."""
    row = Item(
        text=text,
        project=project,
        status=status,
        priority=priority,
        source=source,
        raw_payload_ref=raw_payload_ref,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
