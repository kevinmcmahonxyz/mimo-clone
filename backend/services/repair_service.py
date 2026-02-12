"""Two-phase repair for generated projects.

Phase 1 (auto_fix_project): Programmatic fixes — no API call needed.
Phase 2 (claude_repair_project): Targeted Claude API call for issues
    that need language understanding.
"""

import re

from backend.sandbox.executor import execute_code
from backend.quality import (
    fix_cumulative_solutions,
    validate_project_quality,
)


def auto_fix_project(project_data: dict, errors: list[str]) -> tuple[dict, list[str]]:
    """Phase 1: fix what we can programmatically, without an API call.

    Handles:
      - expected_output mismatches (re-execute and replace)
      - apostrophe in single-quoted strings (swap to double quotes)
      - mock_inputs count mismatches (backfill from later steps)

    Returns (fixed_project, remaining_errors).
    """
    steps = project_data.get("steps", [])

    # --- Fix apostrophe in single-quoted strings ---
    _fix_apostrophe_quotes(steps)

    # --- Backfill mock_inputs from later steps ---
    _fix_mock_inputs(steps)

    # --- Fix expected_output by re-executing accumulated code ---
    _fix_expected_outputs(steps)

    # Re-validate to find remaining errors
    remaining = validate_project_quality(project_data)
    return project_data, remaining


def claude_repair_project(project_data: dict, errors: list[str]) -> dict | None:
    """Phase 2: ask Claude to fix issues that need language understanding.

    Returns the repaired project dict, or None if repair failed.
    """
    from backend.services.claude_service import repair_project

    repaired = repair_project(project_data, errors)
    if not repaired:
        return None

    # Post-process the repaired project the same way we do after generation
    fix_cumulative_solutions(repaired)
    repaired["full_solution"] = "\n".join(
        step["solution"] for step in repaired["steps"]
    )

    # Verify the full solution actually runs
    last_step = repaired["steps"][-1] if repaired["steps"] else {}
    mock_inputs = last_step.get("mock_inputs", [])
    result = execute_code(repaired["full_solution"], mock_inputs)
    if not result["success"]:
        return None

    return repaired


# ---------------------------------------------------------------------------
# Programmatic fix helpers
# ---------------------------------------------------------------------------

def _fix_apostrophe_quotes(steps: list[dict]):
    """Swap single-quoted strings containing apostrophes to double quotes."""
    pattern = re.compile(r"'([^']*[a-zA-Z]'[a-zA-Z][^']*)'")
    for step in steps:
        solution = step.get("solution", "")
        step["solution"] = pattern.sub(r'"\1"', solution)


def _fix_mock_inputs(steps: list[dict]):
    """Backfill mock_inputs from later steps when count is insufficient."""
    # Collect the most complete mock_inputs list (from the last step)
    all_mocks = []
    for step in reversed(steps):
        mocks = step.get("mock_inputs", [])
        if len(mocks) > len(all_mocks):
            all_mocks = list(mocks)
    if not all_mocks:
        return

    # Walk forward, ensuring each step has enough mock_inputs
    accumulated_code = ""
    for step in steps:
        if accumulated_code:
            accumulated_code += "\n" + step["solution"]
        else:
            accumulated_code = step["solution"]

        input_count = len(re.findall(r"\binput\s*\(", accumulated_code))
        current_mocks = step.get("mock_inputs", [])

        if input_count > len(current_mocks):
            # Backfill from the master list
            step["mock_inputs"] = all_mocks[:input_count]


def _fix_expected_outputs(steps: list[dict]):
    """Re-execute accumulated code at each step and replace expected_output."""
    import sys
    accumulated_code = ""
    for step in steps:
        if accumulated_code:
            accumulated_code += "\n" + step["solution"]
        else:
            accumulated_code = step["solution"]

        mock_inputs = step.get("mock_inputs", [])
        result = execute_code(accumulated_code, mock_inputs)

        if result["success"]:
            old_output = step.get("expected_output", "")
            new_output = result.get("output", "")
            if old_output != new_output:
                print(f"[DEBUG] Step {step['step_num']}: Updated expected_output", file=sys.stderr)
                print(f"  Old: {repr(old_output[:80])}", file=sys.stderr)
                print(f"  New: {repr(new_output[:80])}", file=sys.stderr)
            step["expected_output"] = new_output
