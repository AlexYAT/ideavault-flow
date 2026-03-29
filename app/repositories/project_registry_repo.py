"""Persistence for :class:`~app.db.tables.ProjectRegistry` (UI project cards)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.project_constants import SYSTEM_NULL_PROJECT_NAME
from app.db.tables import Item, ProjectRegistry


def get(db: Session, name: str) -> ProjectRegistry | None:
    return db.get(ProjectRegistry, name)


def list_all(db: Session) -> list[ProjectRegistry]:
    return list(db.scalars(select(ProjectRegistry).order_by(ProjectRegistry.name.asc())).all())


def create(db: Session, *, name: str, description: str) -> ProjectRegistry:
    row = ProjectRegistry(name=name, description=description or "", is_system=0)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_description(db: Session, *, name: str, description: str) -> ProjectRegistry | None:
    row = db.get(ProjectRegistry, name)
    if row is None:
        return None
    row.description = description or ""
    db.commit()
    db.refresh(row)
    return row


def upsert_description(db: Session, *, name: str, description: str) -> ProjectRegistry:
    """Создать карточку или обновить описание (в т.ч. у системного ``Null``)."""
    row = db.get(ProjectRegistry, name)
    if row is None:
        row = ProjectRegistry(name=name, description=description or "", is_system=0)
        db.add(row)
    else:
        row.description = description or ""
    db.commit()
    db.refresh(row)
    return row


def delete_non_system(db: Session, *, name: str) -> bool:
    """Удалить строку реестра; ``False`` если нет строки или системный проект."""
    row = db.get(ProjectRegistry, name)
    if row is None or row.is_system:
        return False
    db.delete(row)
    db.commit()
    return True


def list_union_names(db: Session) -> list[str]:
    """Имена из реестра ∪ ненулевые ``items.project`` для выпадающих списков UI."""
    reg = {r.name for r in list_all(db)}
    stmt = select(Item.project).where(Item.project.isnot(None)).distinct()
    from_items = {str(x) for x in db.scalars(stmt).all() if x}
    names = reg | from_items

    def sort_key(n: str) -> tuple[int, str]:
        return (0 if n == SYSTEM_NULL_PROJECT_NAME else 1, n.lower())

    return sorted(names, key=sort_key)
