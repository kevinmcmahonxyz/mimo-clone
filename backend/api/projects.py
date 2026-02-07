import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Optional

from backend.storage.database import Project, Progress, get_session

router = APIRouter(tags=["projects"])


@router.get("/projects")
def list_projects(
    level: Optional[int] = Query(None),
    tier: Optional[int] = Query(None),
    session: Session = Depends(get_session),
):
    stmt = select(Project)
    if level is not None:
        stmt = stmt.where(Project.level_id == level)
    if tier is not None:
        stmt = stmt.where(Project.tier == tier)
    stmt = stmt.order_by(Project.level_id, Project.tier)

    projects = session.exec(stmt).all()
    return [
        {
            "id": p.id,
            "level_id": p.level_id,
            "tier": p.tier,
            "name": p.name,
            "description": p.description,
            "concepts_used": json.loads(p.concepts_used),
            "total_lines": p.total_lines,
            "difficulty_rating": p.difficulty_rating,
            "estimated_minutes": p.estimated_minutes,
        }
        for p in projects
    ]


@router.get("/projects/{project_id}")
def get_project(project_id: str, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": project.id,
        "level_id": project.level_id,
        "tier": project.tier,
        "name": project.name,
        "description": project.description,
        "learning_goals": json.loads(project.learning_goals),
        "concepts_used": json.loads(project.concepts_used),
        "total_lines": project.total_lines,
        "steps": json.loads(project.steps),
        "full_solution": project.full_solution,
        "difficulty_rating": project.difficulty_rating,
        "estimated_minutes": project.estimated_minutes,
    }


@router.get("/progress")
def get_progress(
    user_id: str = "default", session: Session = Depends(get_session)
):
    progress = session.exec(
        select(Progress).where(Progress.user_id == user_id)
    ).all()
    return [
        {
            "project_id": p.project_id,
            "step_num": p.step_num,
            "completed": p.completed,
            "completed_at": p.completed_at,
        }
        for p in progress
    ]


@router.post("/progress/complete")
def mark_complete(
    data: dict,
    session: Session = Depends(get_session),
):
    user_id = data.get("user_id", "default")
    project_id = data["project_id"]
    step_num = data["step_num"]
    code = data.get("code", "")

    existing = session.exec(
        select(Progress).where(
            Progress.user_id == user_id,
            Progress.project_id == project_id,
            Progress.step_num == step_num,
        )
    ).first()

    if existing:
        existing.completed = True
        existing.completed_at = __import__("datetime").datetime.utcnow().isoformat()
        existing.code = code
    else:
        progress = Progress(
            user_id=user_id,
            project_id=project_id,
            step_num=step_num,
            completed=True,
            completed_at=__import__("datetime").datetime.utcnow().isoformat(),
            code=code,
        )
        session.add(progress)

    session.commit()
    return {"status": "ok"}
