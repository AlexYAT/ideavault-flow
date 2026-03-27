"""CRUD for RAG documents, chunks, and GitHub bindings."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.tables import RagChunk, RagDocument, RagGithubBinding


def delete_documents_for_project(db: Session, *, project: str | None) -> int:
    """Remove all knowledge docs (and chunks via ORM) for this scope. ``None`` = global only."""
    q = select(RagDocument)
    if project is None:
        q = q.where(RagDocument.project.is_(None))
    else:
        q = q.where(RagDocument.project == project)
    docs = list(db.scalars(q).all())
    n = len(docs)
    for d in docs:
        db.delete(d)
    db.commit()
    return n


def add_document_with_chunks(
    db: Session,
    *,
    project: str | None,
    source_type: str,
    source_uri: str,
    title: str,
    body: str,
    chunk_texts: list[str],
) -> RagDocument:
    """Persist one document and its chunk rows."""
    doc = RagDocument(
        project=project,
        source_type=source_type,
        source_uri=source_uri,
        title=title,
        body=body,
    )
    db.add(doc)
    db.flush()
    for i, chunk in enumerate(chunk_texts):
        db.add(
            RagChunk(
                document_id=doc.id,
                chunk_index=i,
                text=chunk,
                project=project,
            )
        )
    db.commit()
    db.refresh(doc)
    return doc


def count_documents(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(RagDocument)) or 0)


def count_chunks(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(RagChunk)) or 0)


def count_projects_with_documents(db: Session) -> int:
    stmt = select(func.count(func.distinct(RagDocument.project))).where(RagDocument.project.isnot(None))
    return int(db.scalar(stmt) or 0)


def get_github_binding(db: Session, project: str) -> RagGithubBinding | None:
    return db.get(RagGithubBinding, project)


def upsert_github_binding(
    db: Session,
    *,
    project: str,
    repo_full: str,
    branch: str = "main",
    paths: list[str] | None = None,
) -> RagGithubBinding:
    """``repo_full`` is ``owner/repo``. ``paths`` defaults to README.md only."""
    paths = paths or ["README.md"]
    row = db.get(RagGithubBinding, project)
    payload = json.dumps(paths, ensure_ascii=False)
    if row is None:
        row = RagGithubBinding(project=project, repo_full=repo_full, branch=branch, paths_json=payload)
        db.add(row)
    else:
        row.repo_full = repo_full
        row.branch = branch
        row.paths_json = payload
    db.commit()
    db.refresh(row)
    return row


def set_github_paths(db: Session, *, project: str, paths: list[str]) -> RagGithubBinding | None:
    row = db.get(RagGithubBinding, project)
    if row is None:
        return None
    row.paths_json = json.dumps(paths, ensure_ascii=False)
    db.commit()
    db.refresh(row)
    return row


def list_github_paths(db: Session, project: str) -> list[str]:
    row = db.get(RagGithubBinding, project)
    if row is None:
        return []
    try:
        data: Any = json.loads(row.paths_json)
        return list(data) if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
