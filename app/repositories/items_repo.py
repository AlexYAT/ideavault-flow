"""Persistence for `Item` rows."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.tables import Item
from app.utils.source_dedupe import normalize_note_text


def list_items(db: Session, *, project: str | None = None, limit: int = 100) -> Sequence[Item]:
    """Return recent items by ``created_at`` desc, optionally filtered by project."""
    stmt = select(Item).order_by(Item.created_at.desc()).limit(limit)
    if project is not None:
        stmt = stmt.where(Item.project == project)
    return db.scalars(stmt).all()


def get_item(db: Session, item_id: int) -> Item | None:
    """Load a single item by id."""
    return db.get(Item, item_id)


def set_item_project(db: Session, item_id: int, project: str | None) -> Item | None:
    """Update ``Item.project`` (``None`` = глобальная область)."""
    row = db.get(Item, item_id)
    if row is None:
        return None
    row.project = project
    db.commit()
    db.refresh(row)
    return row


def find_item_by_normalized_text(
    db: Session,
    *,
    normalized_text: str,
    project: str | None,
) -> Item | None:
    """
    Return an existing row in ``project`` (or global ``NULL``) whose body normalizes to
    ``normalized_text``, or ``None``.

    Uses in-Python comparison so no schema change is required.
    """
    stmt = select(Item)
    if project is None:
        stmt = stmt.where(Item.project.is_(None))
    else:
        stmt = stmt.where(Item.project == project)
    for row in db.scalars(stmt).all():
        if normalize_note_text(row.text) == normalized_text:
            return row
    return None


def update_item_text(db: Session, item_id: int, text: str) -> Item | None:
    """Обновить только текст заметки."""
    row = db.get(Item, item_id)
    if row is None:
        return None
    row.text = text
    db.commit()
    db.refresh(row)
    return row


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
    """Insert a new item."""
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


def count_by_project(db: Session, *, project: str) -> int:
    """Count items whose ``project`` column equals ``project``."""
    stmt = select(func.count()).select_from(Item).where(Item.project == project)
    return int(db.scalar(stmt) or 0)


def list_distinct_project_names(db: Session) -> list[str]:
    """Return unique non-null project names sorted alphabetically."""
    stmt = (
        select(Item.project)
        .where(Item.project.isnot(None))
        .distinct()
        .order_by(Item.project.asc())
    )
    rows = db.execute(stmt).scalars().all()
    return [str(name) for name in rows if name]


def count_items_total(db: Session) -> int:
    """All rows in ``items``."""
    return int(db.scalar(select(func.count()).select_from(Item)) or 0)


def count_items_with_nonnull_project(db: Session) -> int:
    """Rows where ``project`` is set (not ``NULL``)."""
    stmt = select(func.count()).select_from(Item).where(Item.project.isnot(None))
    return int(db.scalar(stmt) or 0)
