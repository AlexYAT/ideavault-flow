"""Load plain-text sources: local paths and GitHub raw URLs (no Git API auth)."""

from __future__ import annotations

from pathlib import Path

import httpx


def read_local_text_file(path: Path) -> str:
    """Read ``.md`` / ``.txt`` as UTF-8 (strip BOM if present)."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode("utf-8", errors="replace")


def github_raw_url(repo_full: str, branch: str, path: str) -> str:
    """
    Build ``https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}``.

    ``repo_full`` must be ``owner/repo`` (one slash).
    """
    repo_full = repo_full.strip().strip("/")
    if "/" not in repo_full:
        raise ValueError("repo_full must look like owner/repo")
    owner, _, repo = repo_full.partition("/")
    if not owner or not repo:
        raise ValueError("repo_full must look like owner/repo")
    rel = path.lstrip("/")
    b = branch.strip() or "main"
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/{rel}"


def fetch_github_text(repo_full: str, branch: str, path: str, *, timeout: float = 45.0) -> str:
    """GET raw file content; raises :class:`httpx.HTTPError` on failure."""
    url = github_raw_url(repo_full, branch, path)
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
    return resp.text
