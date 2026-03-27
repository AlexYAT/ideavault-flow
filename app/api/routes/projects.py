"""Project listing and session-oriented helpers (API mirror of bot commands)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services import mvp_api_service, project_service

router = APIRouter()


class CurrentProjectBody(BaseModel):
    """Set active project for a logical user (MVP: string id). TODO: JWT subject."""

    user_id: str
    project: str | None


@router.get("/projects", response_model=list[str])
def list_projects(db: Session = Depends(get_db)) -> list[str]:
    """Distinct non-null project names from items, sorted alphabetically."""
    return mvp_api_service.list_projects(db)


@router.post("/projects/current")
def set_current(body: CurrentProjectBody, db: Session = Depends(get_db)) -> dict[str, str | None]:
    """API equivalent of /set and /clear."""
    project_service.set_current_project(db, body.user_id, body.project)
    return {"current_project": body.project}
