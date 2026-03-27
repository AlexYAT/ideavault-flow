"""Orchestrate ingestion: local ``data/knowledge/…`` + optional GitHub manifest."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories import rag_repo
from app.rag import chunking, sources

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_ROOT = _PROJECT_ROOT / "data" / "knowledge"


def knowledge_dir(project: str | None) -> Path:
    """``data/knowledge/<project>`` or ``data/knowledge/_global`` when ``project`` is None."""
    if project is None:
        return _KNOWLEDGE_ROOT / "_global"
    return _KNOWLEDGE_ROOT / project


def _index_single_text(
    db: Session,
    *,
    project: str | None,
    source_type: str,
    source_uri: str,
    title: str,
    body: str,
) -> None:
    chunks = chunking.chunk_text(body)
    if not chunks:
        logger.info("skip empty document %s", source_uri)
        return
    rag_repo.add_document_with_chunks(
        db,
        project=project,
        source_type=source_type,
        source_uri=source_uri,
        title=title,
        body=body,
        chunk_texts=chunks,
    )


def index_local_folder(db: Session, *, project: str | None) -> int:
    """
    Index all ``*.md`` and ``*.txt`` under the scoped knowledge folder.

    Returns number of files successfully indexed (skipped empty).
    """
    root = knowledge_dir(project)
    if not root.is_dir():
        root.mkdir(parents=True, exist_ok=True)
        return 0
    count = 0
    for pattern in ("**/*.md", "**/*.txt"):
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            try:
                body = sources.read_local_text_file(path)
            except OSError as exc:
                logger.warning("local read failed %s: %s", path, exc)
                continue
            rel = path.relative_to(root).as_posix()
            _index_single_text(
                db,
                project=project,
                source_type="local",
                source_uri=f"local:{rel}",
                title=path.name,
                body=body,
            )
            count += 1
    return count


def index_github_for_project(db: Session, *, project: str) -> int:
    """Fetch whitelisted paths from bound ``owner/repo``; returns count of files indexed."""
    bind = rag_repo.get_github_binding(db, project)
    if bind is None:
        return 0
    paths = rag_repo.list_github_paths(db, project)
    if not paths:
        paths = ["README.md"]
    n = 0
    for p in paths:
        try:
            body = sources.fetch_github_text(bind.repo_full, bind.branch, p)
        except Exception as exc:
            logger.warning("github fetch failed %s/%s: %s", bind.repo_full, p, exc)
            continue
        uri = f"github:{bind.repo_full}@{bind.branch}:{p}"
        _index_single_text(
            db,
            project=project,
            source_type="github",
            source_uri=uri,
            title=p.split("/")[-1] or p,
            body=body,
        )
        n += 1
    return n


def reindex_project_scope(db: Session, *, project: str | None) -> dict[str, int]:
    """
    Drop existing documents for the scope, then re-load local folder + (if named) GitHub binding.

    ``project`` ``None`` only reindexes global folder (no GitHub binding table row).
    """
    deleted = rag_repo.delete_documents_for_project(db, project=project)
    local_n = index_local_folder(db, project=project)
    gh_n = 0
    if project is not None:
        gh_n = index_github_for_project(db, project=project)
    return {"deleted_documents": deleted, "indexed_local_files": local_n, "indexed_github_files": gh_n}
