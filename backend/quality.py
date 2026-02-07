"""Shared quality-checking utilities for generated projects.

Used by generation.py, generate_seeds.py, and repair_service.py to avoid
duplicating validation logic.
"""

import re

from backend.sandbox.executor import execute_code


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAGUE_PATTERNS = [
    re.compile(r"\bprint a message\b", re.IGNORECASE),
    re.compile(r"\bprint a welcome\b", re.IGNORECASE),
    re.compile(r"\bprint a greeting\b", re.IGNORECASE),
    re.compile(r"\bstore the result\b(?!\s+in\s+a\s+variable\s+called)", re.IGNORECASE),
    re.compile(r"\bstore it in a variable\b(?!\s+called)", re.IGNORECASE),
    re.compile(r"\bcreate a variable\b(?!\s+called)", re.IGNORECASE),
    re.compile(r"\bsave (?:it |the \w+ )?(?:in|to) a variable\b(?!\s+called)", re.IGNORECASE),
    re.compile(r"\buse an? (?:appropriate|suitable|relevant)\b", re.IGNORECASE),
    re.compile(r"\bprint an? (?:appropriate|suitable|relevant)\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Normalize whitespace: strip trailing spaces per line, remove trailing empty lines."""
    lines = text.replace("\r\n", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def fix_cumulative_solutions(project_data: dict):
    """If Claude returned cumulative solutions, strip them down to incremental."""
    steps = project_data.get("steps", [])
    if len(steps) < 2:
        return

    prev_solution_lines = []
    for step in steps:
        solution = step.get("solution", "")
        solution_lines = solution.split("\n")

        if len(solution_lines) > len(prev_solution_lines) and prev_solution_lines:
            is_cumulative = all(
                solution_lines[i] == prev_solution_lines[i]
                for i in range(len(prev_solution_lines))
            )
            if is_cumulative:
                new_lines = solution_lines[len(prev_solution_lines):]
                step["solution"] = "\n".join(new_lines)

        prev_solution_lines = solution_lines


# ---------------------------------------------------------------------------
# Quality validation
# ---------------------------------------------------------------------------

def validate_project_quality(project_data: dict) -> list[str]:
    """Run quality checks on a generated project. Returns list of error messages."""
    errors = []
    steps = project_data.get("steps", [])

    # 1. Step-by-step execution and output matching
    accumulated_code = ""
    for step in steps:
        if accumulated_code:
            accumulated_code += "\n" + step["solution"]
        else:
            accumulated_code = step["solution"]

        mock_inputs = step.get("mock_inputs", [])
        result = execute_code(accumulated_code, mock_inputs)

        if not result["success"]:
            errors.append(
                f"Step {step['step_num']}: execution failed — "
                f"{result.get('error', 'unknown error')[:80]}"
            )
            continue

        expected = step.get("expected_output", "")
        if expected:
            actual = result.get("output", "")
            if normalize(actual) != normalize(expected):
                errors.append(
                    f"Step {step['step_num']}: output mismatch. "
                    f"Expected: {repr(expected[:100])} Got: {repr(actual[:100])}"
                )

    # 2. Instruction specificity
    for step in steps:
        instruction = step.get("instruction", "")
        for pattern in VAGUE_PATTERNS:
            match = pattern.search(instruction)
            if match:
                errors.append(
                    f"Step {step['step_num']}: vague instruction — '{match.group()}'"
                )

    # 3. Apostrophe in single-quoted strings
    for step in steps:
        solution = step.get("solution", "")
        for sq_match in re.finditer(r"'([^']*)'", solution):
            content = sq_match.group(1)
            if re.search(r"[a-zA-Z]'[a-zA-Z]", content):
                errors.append(
                    f"Step {step['step_num']}: apostrophe in single-quoted string: "
                    f"{sq_match.group()}"
                )

    # 4. Mock inputs coverage
    accumulated_code = ""
    for step in steps:
        if accumulated_code:
            accumulated_code += "\n" + step["solution"]
        else:
            accumulated_code = step["solution"]

        input_count = len(re.findall(r"\binput\s*\(", accumulated_code))
        mock_count = len(step.get("mock_inputs", []))
        if input_count > 0 and mock_count < input_count:
            errors.append(
                f"Step {step['step_num']}: {input_count} input() calls "
                f"but only {mock_count} mock_inputs"
            )

    return errors
