import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional

from backend.storage.database import Lesson, Project, get_session
from backend.services.claude_service import generate_project, generate_hint
from backend.sandbox.executor import execute_code
from backend.config import settings

router = APIRouter(tags=["generation"])


class GenerateProjectRequest(BaseModel):
    level_id: int
    tier: int
    theme: Optional[str] = None
    avoid_concepts: Optional[list[str]] = None


class GenerateHintRequest(BaseModel):
    instruction: str
    code: str
    error: Optional[str] = None


@router.post("/generate/project")
def gen_project(req: GenerateProjectRequest, session: Session = Depends(get_session)):
    if not settings.claude_api_key:
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    lesson = session.get(Lesson, req.level_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Level not found")

    concepts = json.loads(lesson.concepts)

    project_data = generate_project(
        level_id=req.level_id,
        tier=req.tier,
        concepts=concepts,
        theme=req.theme,
        avoid_concepts=req.avoid_concepts,
    )

    if not project_data:
        raise HTTPException(status_code=500, detail="Failed to generate project")

    # Fix cumulative solutions: ensure each step's solution is only the NEW code
    _fix_cumulative_solutions(project_data)

    # Rebuild full_solution from step solutions (don't trust Claude's version)
    project_data["full_solution"] = "\n".join(
        step["solution"] for step in project_data["steps"]
    )

    # Validate: run the full solution to catch syntax errors, bad quotes, etc.
    last_step = project_data["steps"][-1] if project_data["steps"] else {}
    mock_inputs = last_step.get("mock_inputs", [])
    validation = execute_code(project_data["full_solution"], mock_inputs)
    if not validation["success"]:
        raise HTTPException(
            status_code=422,
            detail=f"Generated code had errors — click Retry to generate a new project.",
        )

    # Save to database
    project = Project(
        id=project_data["id"],
        level_id=project_data["level_id"],
        tier=project_data["tier"],
        name=project_data["name"],
        description=project_data["description"],
        learning_goals=json.dumps(project_data["learning_goals"]),
        concepts_used=json.dumps(project_data["concepts_used"]),
        total_lines=project_data["total_lines"],
        steps=json.dumps(project_data["steps"]),
        full_solution=project_data["full_solution"],
        difficulty_rating=project_data.get("difficulty_rating", 1),
        estimated_minutes=project_data.get("estimated_minutes", 10),
        is_generated=True,
    )
    session.add(project)
    session.commit()

    return project_data


def _fix_cumulative_solutions(project_data: dict):
    """If Claude returned cumulative solutions, strip them down to incremental."""
    steps = project_data.get("steps", [])
    if len(steps) < 2:
        return

    prev_solution_lines = []
    for step in steps:
        solution = step.get("solution", "")
        solution_lines = solution.split("\n")

        # Check if this step's solution starts with all previous lines (cumulative)
        if len(solution_lines) > len(prev_solution_lines) and prev_solution_lines:
            is_cumulative = all(
                solution_lines[i] == prev_solution_lines[i]
                for i in range(len(prev_solution_lines))
            )
            if is_cumulative:
                # Strip previous lines — keep only the new code
                new_lines = solution_lines[len(prev_solution_lines):]
                step["solution"] = "\n".join(new_lines)

        # Track full code so far for next iteration
        prev_solution_lines = solution_lines


@router.post("/generate/hint")
def gen_hint(req: GenerateHintRequest):
    if not settings.claude_api_key:
        return {"hint": "Try re-reading the instruction carefully and check your syntax."}

    hint = generate_hint(
        instruction=req.instruction,
        code=req.code,
        error=req.error,
    )
    return {"hint": hint}
