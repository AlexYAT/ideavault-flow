"""Read-only vault aggregates (demo-friendly)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.stats import VaultStatsOut
from app.services import mvp_api_service

router = APIRouter()


@router.get(
    "/stats",
    response_model=VaultStatsOut,
    summary="Vault counters",
    description="Returns total notes, distinct project count, and notes assigned to a project. Single cheap read per counter.",
)
def vault_stats(db: Session = Depends(get_db)) -> VaultStatsOut:
    """Aggregated counts over the `items` table for quick demo checks."""
    return mvp_api_service.get_vault_stats(db)
