"""Liveness and readiness style checks."""

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Liveness",
    description="Process is up; does not ping the database.",
)
def health() -> dict[str, str]:
    """Return ``{\"status\": \"ok\"}`` for load balancers and quick checks."""
    return {"status": "ok"}
