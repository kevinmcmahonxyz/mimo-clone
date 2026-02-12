import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from starlette.responses import StreamingResponse
from typing import Optional

from backend.storage.database import Lesson, Project, engine
from backend.services.claude_service import generate_project, generate_hint
from backend.services.repair_service import auto_fix_project, claude_repair_project
from backend.quality import fix_cumulative_solutions, validate_project_quality
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


def _sse(status: str, message: str, **extra) -> str:
    payload = {"status": status, "message": message, **extra}
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/generate/project")
def gen_project(req: GenerateProjectRequest):
    if not settings.claude_api_key:
        raise HTTPException(status_code=503, detail="Claude API key not configured")

    def generate_stream():
        # Use our own session inside the generator (outside FastAPI DI scope)
        with Session(engine) as session:
            lesson = session.get(Lesson, req.level_id)
            if not lesson:
                yield _sse("error", "Level not found")
                return

            concepts = json.loads(lesson.concepts)
            generation_context = lesson.generation_context or ""

            # --- Stage: generating ---
            yield _sse("generating", "Generating project with Claude...")

            project_data = generate_project(
                level_id=req.level_id,
                tier=req.tier,
                concepts=concepts,
                generation_context=generation_context,
                theme=req.theme,
                avoid_concepts=req.avoid_concepts,
            )

            if not project_data:
                yield _sse("error", "Failed to generate project — click Retry.")
                return

            # Fix cumulative solutions
            fix_cumulative_solutions(project_data)

            # Rebuild full_solution from step solutions
            project_data["full_solution"] = "\n".join(
                step["solution"] for step in project_data["steps"]
            )

            # --- Stage: validating ---
            yield _sse("validating", "Validating generated code...")

            last_step = project_data["steps"][-1] if project_data["steps"] else {}
            mock_inputs = last_step.get("mock_inputs", [])
            validation = execute_code(project_data["full_solution"], mock_inputs)
            if not validation["success"]:
                yield _sse("error", "Generated code had errors — click Retry.")
                return

            # --- Stage: quality_check ---
            yield _sse("quality_check", "Running quality checks...")

            # ALWAYS run auto-fix first to ensure expected_output values are correct
            # (especially for projects using random module with seed)
            project_data, _ = auto_fix_project(project_data, [])

            quality_errors = validate_project_quality(project_data)
            if quality_errors:
                # --- Stage: repairing ---
                yield _sse("repairing", "Auto-fixing issues...")

                project_data, remaining = auto_fix_project(project_data, quality_errors)

                # Phase 2: up to 2 Claude repair attempts
                for repair_attempt in range(2):
                    if not remaining:
                        break
                    yield _sse(
                        "claude_repair",
                        f"Asking Claude to repair (attempt {repair_attempt + 1})...",
                    )
                    repaired = claude_repair_project(project_data, remaining)
                    if not repaired:
                        break
                    project_data = repaired
                    remaining = validate_project_quality(project_data)

                if remaining:
                    yield _sse(
                        "error",
                        f"Quality check failed: {'; '.join(remaining[:3])}. Click Retry.",
                    )
                    return

            # --- Stage: saving ---
            yield _sse("saving", "Saving project...")

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

            # --- Stage: done ---
            yield _sse("done", "Project ready!", project=project_data)

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


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
