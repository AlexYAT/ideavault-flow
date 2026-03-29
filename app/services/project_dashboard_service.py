"""
Dashboard проектов: строки для UI, создание/редактирование, удаление с переносом в ``Null``.

Бизнес-правила см. задачу product UI; слой тонкий над repositories.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.project_constants import SYSTEM_NULL_PROJECT_NAME, is_reserved_system_name
from app.db.tables import Item
from app.rag.indexer import knowledge_dir
from app.repositories import items_repo, project_registry_repo, rag_repo


def _marker(deleted_name: str) -> str:
    return f"Из удаленного {deleted_name}"


def item_already_tagged_deleted_from(text: str, deleted_name: str) -> bool:
    """Не дублировать префикс, если он уже есть в начале или первых строках."""
    m = _marker(deleted_name)
    if text.lstrip().startswith(m):
        return True
    for line in text.splitlines()[:4]:
        if line.strip().startswith(m):
            return True
    return False


def knowledge_folder_has_files(project: str) -> bool:
    """Есть ли локальные ``.md`` / ``.txt`` в ``data/knowledge/<project>``."""
    d = knowledge_dir(project)
    if not d.is_dir():
        return False
    return any(d.glob("*.md")) or any(d.glob("*.txt"))


def list_local_rag_files(project: str) -> list[str]:
    """
    Относительные пути всех файлов под ``data/knowledge/<project>`` (рекурсивно).

    Использует :func:`~app.rag.indexer.knowledge_dir` для корня проекта.
    """
    base = knowledge_dir(project)
    if not base.exists() or not base.is_dir():
        return []
    return sorted(
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file()
    )


@dataclass(frozen=True)
class ProjectDashboardRow:
    """Готовые поля для шаблона дашборда (без логики в Jinja)."""

    name: str
    name_url: str
    description: str
    is_system: bool
    has_items: bool
    has_local_rag: bool
    has_github_bind: bool
    num_items: int
    num_local_rag_files: int
    open_url: str
    edit_url: str
    delete_confirm_url: str


def _row(db: Session, name: str) -> ProjectDashboardRow:
    reg = project_registry_repo.get(db, name)
    desc = (reg.description if reg else "") or ""
    is_sys = bool(reg and reg.is_system)
    n_items = items_repo.count_by_project(db, project=name)
    local_files = list_local_rag_files(name)
    has_bind = rag_repo.get_github_binding(db, name) is not None
    q = quote(name, safe="")
    return ProjectDashboardRow(
        name=name,
        name_url=q,
        description=desc,
        is_system=is_sys,
        has_items=n_items > 0,
        has_local_rag=knowledge_folder_has_files(name),
        has_github_bind=has_bind,
        num_items=n_items,
        num_local_rag_files=len(local_files),
        open_url=f"/ui/project/{q}",
        edit_url=f"/ui/project/{q}/edit",
        delete_confirm_url=f"/ui/project/{q}/delete-confirm",
    )


def list_dashboard_rows(db: Session) -> list[ProjectDashboardRow]:
    names = project_registry_repo.list_union_names(db)
    return [_row(db, n) for n in names]


def create_project(db: Session, *, name: str, description: str) -> None:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("Укажите имя проекта")
    if is_reserved_system_name(cleaned):
        raise ValueError("Имя зарезервировано")
    if project_registry_repo.get(db, cleaned):
        raise ValueError("Проект с таким именем уже есть")
    project_registry_repo.create(db, name=cleaned, description=description or "")


def update_project(db: Session, *, name: str, description: str) -> None:
    project_registry_repo.upsert_description(db, name=name, description=description or "")


def delete_project_cascade(db: Session, *, name: str) -> None:
    """
    Удалить проект: заметки → ``Null`` с префиксом, очистить RAG/GitHub bind, строка реестра (не system).
    Одна транзакция на уровне сессии.
    """
    if name == SYSTEM_NULL_PROJECT_NAME:
        raise ValueError("Нельзя удалить служебный проект Null")
    rows = list(db.scalars(select(Item).where(Item.project == name)).all())
    for row in rows:
        if not item_already_tagged_deleted_from(row.text, name):
            row.text = f"{_marker(name)}\n" + row.text
        row.project = SYSTEM_NULL_PROJECT_NAME
    rag_repo.delete_documents_for_project(db, project=name, commit=False)
    rag_repo.delete_github_binding(db, name, commit=False)
    reg = project_registry_repo.get(db, name)
    if reg is not None and reg.is_system == 0:
        db.delete(reg)
    db.commit()
