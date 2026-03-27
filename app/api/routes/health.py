"""Liveness and readiness style checks."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Return service health (no DB check in skeleton)."""
    return {"status": "ok"}
