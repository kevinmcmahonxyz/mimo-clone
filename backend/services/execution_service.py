import json
from sqlmodel import Session

from backend.storage.database import Project
from backend.sandbox.executor import execute_code
from backend.services.validation_service import validate_output


def run_and_validate(
    project_id: str,
    step_num: int,
    code: str,
    accumulated_code: str,
    session: Session,
) -> dict:
    """Execute user code and validate against expected output for the step."""
    project = session.get(Project, project_id)
    if not project:
        return {"success": False, "output": "", "match": False, "feedback": "Project not found."}

    steps = json.loads(project.steps)
    step = None
    for s in steps:
        if s["step_num"] == step_num:
            step = s
            break

    if not step:
        return {"success": False, "output": "", "match": False, "feedback": "Step not found."}

    # Combine accumulated code with current step code
    full_code = accumulated_code + "\n" + code if accumulated_code.strip() else code

    # Get mock inputs for this step
    mock_inputs = step.get("mock_inputs", [])

    # Execute
    result = execute_code(full_code, mock_inputs)

    if not result["success"]:
        return {
            "success": False,
            "output": result.get("output", ""),
            "error": result["error"],
            "match": False,
            "feedback": f"Error: {result['error']}",
        }

    # Validate output
    expected = step.get("expected_output", "")
    validation = validate_output(result["output"], expected)

    return {
        "success": True,
        "output": result["output"],
        "match": validation["match"],
        "feedback": validation["feedback"],
    }
