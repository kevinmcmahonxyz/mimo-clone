import json
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.storage.database import Lesson, get_session

router = APIRouter(tags=["lessons"])


@router.get("/lessons")
def list_lessons(session: Session = Depends(get_session)):
    lessons = session.exec(select(Lesson).order_by(Lesson.id)).all()
    return [
        {
            "id": l.id,
            "name": l.name,
            "description": l.description,
            "concepts": json.loads(l.concepts),
            "prerequisite_id": l.prerequisite_id,
        }
        for l in lessons
    ]


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {
        "id": lesson.id,
        "name": lesson.name,
        "description": lesson.description,
        "concepts": json.loads(lesson.concepts),
        "examples": json.loads(lesson.examples),
        "prerequisite_id": lesson.prerequisite_id,
    }
