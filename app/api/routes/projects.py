"""Project listing and session-oriented helpers (API mirror of bot commands)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services import project_service

router = APIRouter()


class CurrentProjectBody(BaseModel):
    """Set active project for a logical user (MVP: string id). TODO: JWT subject."""

    user_id: str
    project: str | None


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    """Distinct project names inferred from items."""
    names = project_service.list_distinct_projects(db)
    return {"projects": names}


@router.post("/projects/current")
def set_current(body: CurrentProjectBody, db: Session = Depends(get_db)) -> dict[str, str | None]:
    """API equivalent of /set and /clear."""
    project_service.set_current_project(db, body.user_id, body.project)
    return {"current_project": body.project}
