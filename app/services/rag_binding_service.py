"""
Validate GitHub raw paths before saving RAG bindings (UI / future callers).

Delegates URL building and HTTP checks to :mod:`app.rag.sources`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.rag import sources


@dataclass(frozen=True)
class GithubPathsValidationResult:
    """Partition of user paths into reachable vs missing on raw.githubusercontent.com."""

    valid: list[str]
    invalid: list[str]

    @property
    def all_invalid(self) -> bool:
        return bool(self.invalid) and not self.valid

    @property
    def all_valid(self) -> bool:
        return bool(self.valid) and not self.invalid


def validate_github_paths(
    repo_full: str,
    branch: str,
    paths: list[str],
    *,
    probe: Callable[..., bool] | None = None,
) -> GithubPathsValidationResult | None:
    """
    Check each non-empty path; return ``None`` if ``paths`` is empty.

    ``probe`` defaults to :func:`~app.rag.sources.probe_github_raw` (injectable for tests).
    """
    fn = probe or sources.probe_github_raw
    cleaned = [p.strip() for p in paths if p and str(p).strip()]
    if not cleaned:
        return None
    repo = (repo_full or "").strip()
    br = (branch or "main").strip() or "main"
    valid: list[str] = []
    invalid: list[str] = []
    try:
        sources.github_raw_url(repo, br, cleaned[0])
    except ValueError:
        return GithubPathsValidationResult(valid=[], invalid=cleaned)
    for rel in cleaned:
        if fn(repo, br, rel):
            valid.append(rel)
        else:
            invalid.append(rel)
    return GithubPathsValidationResult(valid=valid, invalid=invalid)


def format_bind_result_message(project: str, result: GithubPathsValidationResult) -> str:
    """User-facing Russian summary after save attempt."""
    pname = project.strip()
    if result.all_invalid:
        bad = ", ".join(result.invalid)
        return (
            f"Не сохранено для «{pname}»: ни один файл не найден на GitHub ({bad}). "
            "Проверьте owner/repo, ветку и пути."
        )
    if result.all_valid:
        n = len(result.valid)
        return f"Для проекта «{pname}» сохранено {n} файл(ов). Все пути доступны на GitHub."
    n_ok = len(result.valid)
    bad = ", ".join(result.invalid)
    return f"Для проекта «{pname}» сохранено {n_ok} файл(ов). Не найдены: {bad}."
