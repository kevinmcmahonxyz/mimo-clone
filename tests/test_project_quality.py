"""Quality test suite for Mimo Clone seed projects.

Validates structural integrity, solution execution, instruction quality,
and consistency across all project JSON files.
"""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from backend.quality import VAGUE_PATTERNS

# Path to project data
DATA_DIR = Path(__file__).parent.parent / "data" / "projects"


def get_project_files():
    """Collect all project JSON file paths."""
    return sorted(DATA_DIR.glob("*.json"))


def load_project(path: Path) -> dict:
    """Load and parse a project JSON file."""
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def all_projects():
    """Load all projects once for the test session."""
    projects = {}
    for path in get_project_files():
        projects[path.stem] = load_project(path)
    return projects


def project_ids():
    """Return list of (file_stem) for parametrize."""
    return [p.stem for p in get_project_files()]


# ---------------------------------------------------------------------------
# A. Structural Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("project_id", project_ids())
class TestStructuralValidation:
    """Validate required keys, types, and value ranges."""

    def _load(self, project_id):
        return load_project(DATA_DIR / f"{project_id}.json")

    def test_required_top_level_keys(self, project_id):
        proj = self._load(project_id)
        required = {"id", "level_id", "tier", "name", "steps", "full_solution"}
        missing = required - set(proj.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_level_id_range(self, project_id):
        proj = self._load(project_id)
        assert 1 <= proj["level_id"] <= 9, f"level_id {proj['level_id']} out of range 1-9"

    def test_tier_range(self, project_id):
        proj = self._load(project_id)
        assert proj["tier"] in (1, 2, 3), f"tier {proj['tier']} not in (1, 2, 3)"

    def test_steps_non_empty(self, project_id):
        proj = self._load(project_id)
        assert len(proj["steps"]) > 0, "steps is empty"

    def test_step_nums_sequential(self, project_id):
        proj = self._load(project_id)
        nums = [s["step_num"] for s in proj["steps"]]
        expected = list(range(1, len(nums) + 1))
        assert nums == expected, f"step_nums {nums} != expected {expected}"

    def test_step_required_keys(self, project_id):
        proj = self._load(project_id)
        required = {"step_num", "instruction", "hint", "expected_lines",
                     "expected_output", "mock_inputs", "solution"}
        for step in proj["steps"]:
            missing = required - set(step.keys())
            assert not missing, f"Step {step.get('step_num', '?')} missing keys: {missing}"

    def test_expected_lines_range(self, project_id):
        proj = self._load(project_id)
        for step in proj["steps"]:
            el = step["expected_lines"]
            assert 1 <= el <= 5, (
                f"Step {step['step_num']}: expected_lines={el} out of range 1-5"
            )


# ---------------------------------------------------------------------------
# B. Solution Execution
# ---------------------------------------------------------------------------


def _execute_code(code: str, mock_inputs: list[str]) -> dict:
    """Execute Python code with mocked inputs, return {success, output, error}."""
    if mock_inputs:
        inputs_repr = repr(mock_inputs)
        wrapper = f"""import builtins
_mock_inputs = {inputs_repr}
_input_index = 0

def _mock_input(prompt=''):
    global _input_index
    if prompt:
        print(prompt, end='')
    if _input_index < len(_mock_inputs):
        val = _mock_inputs[_input_index]
        _input_index += 1
        return val
    return ''

builtins.input = _mock_input

"""
        full_code = wrapper + code
    else:
        full_code = code

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(full_code)
        code_path = f.name

    try:
        result = subprocess.run(
            ["python3", code_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "Timeout"}
    finally:
        os.unlink(code_path)


def _normalize(text: str) -> str:
    """Normalize whitespace for comparison."""
    lines = text.replace("\r\n", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


@pytest.mark.parametrize("project_id", project_ids())
class TestSolutionExecution:
    """Validate that project solutions actually run correctly."""

    def _load(self, project_id):
        return load_project(DATA_DIR / f"{project_id}.json")

    def test_full_solution_matches_concatenated_steps(self, project_id):
        proj = self._load(project_id)
        concatenated = "\n".join(s["solution"] for s in proj["steps"])
        assert _normalize(proj["full_solution"]) == _normalize(concatenated), (
            "full_solution does not match concatenated step solutions"
        )

    def test_full_solution_executes(self, project_id):
        proj = self._load(project_id)
        last_step = proj["steps"][-1]
        mock_inputs = last_step.get("mock_inputs", [])
        result = _execute_code(proj["full_solution"], mock_inputs)
        assert result["success"], (
            f"full_solution failed to execute:\n{result['error']}"
        )

    def test_step_outputs_match(self, project_id):
        proj = self._load(project_id)
        accumulated_code = ""
        for step in proj["steps"]:
            if accumulated_code:
                accumulated_code += "\n" + step["solution"]
            else:
                accumulated_code = step["solution"]

            mock_inputs = step.get("mock_inputs", [])
            result = _execute_code(accumulated_code, mock_inputs)

            assert result["success"], (
                f"Step {step['step_num']}: execution failed:\n{result['error']}"
            )

            expected = step.get("expected_output", "")
            if expected:
                assert _normalize(result["output"]) == _normalize(expected), (
                    f"Step {step['step_num']}: output mismatch.\n"
                    f"Expected:\n{repr(expected)}\n"
                    f"Got:\n{repr(result['output'])}"
                )


# ---------------------------------------------------------------------------
# C. Instruction Quality
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_id", project_ids())
class TestInstructionQuality:
    """Validate that instructions are specific, not vague."""

    def _load(self, project_id):
        return load_project(DATA_DIR / f"{project_id}.json")

    def test_no_vague_instructions(self, project_id):
        proj = self._load(project_id)
        for step in proj["steps"]:
            instruction = step["instruction"]
            for pattern in VAGUE_PATTERNS:
                match = pattern.search(instruction)
                assert match is None, (
                    f"Step {step['step_num']}: vague instruction detected — "
                    f"'{match.group()}' in: {instruction[:100]}..."
                )

    def test_no_apostrophe_in_single_quotes(self, project_id):
        """Solution code should not have apostrophes inside single-quoted strings."""
        proj = self._load(project_id)
        # Pattern: single-quoted string containing an apostrophe
        bad_pattern = re.compile(r"'[^']*(?<=[a-zA-Z])'[a-zA-Z][^']*'")
        for step in proj["steps"]:
            solution = step["solution"]
            # Simpler check: look for common apostrophe problems
            # e.g., 'Let's', 'don't', 'it's'
            for match in re.finditer(r"'([^']*)'", solution):
                content = match.group(1)
                # If content contains an unescaped apostrophe pattern
                if re.search(r"[a-zA-Z]'[a-zA-Z]", content):
                    pytest.fail(
                        f"Step {step['step_num']}: apostrophe inside single-quoted string: "
                        f"{match.group()}"
                    )


# ---------------------------------------------------------------------------
# D. Consistency Checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("project_id", project_ids())
class TestConsistencyChecks:
    """Validate internal consistency of project data."""

    def _load(self, project_id):
        return load_project(DATA_DIR / f"{project_id}.json")

    def test_total_lines_approximate(self, project_id):
        proj = self._load(project_id)
        sum_expected = sum(s["expected_lines"] for s in proj["steps"])
        total = proj.get("total_lines", sum_expected)
        # Allow ±3 tolerance
        assert abs(total - sum_expected) <= 3, (
            f"total_lines={total} but sum of expected_lines={sum_expected} (off by {abs(total - sum_expected)})"
        )

    def test_mock_inputs_coverage(self, project_id):
        """Steps with input() in accumulated code should have enough mock_inputs."""
        proj = self._load(project_id)
        accumulated_code = ""
        for step in proj["steps"]:
            if accumulated_code:
                accumulated_code += "\n" + step["solution"]
            else:
                accumulated_code = step["solution"]

            # Count input() calls in accumulated code
            input_count = len(re.findall(r"\binput\s*\(", accumulated_code))
            mock_count = len(step.get("mock_inputs", []))

            if input_count > 0:
                assert mock_count >= input_count, (
                    f"Step {step['step_num']}: {input_count} input() calls "
                    f"but only {mock_count} mock_inputs"
                )

    def test_steps_with_input_have_mock_inputs(self, project_id):
        """If a step's solution contains input(), mock_inputs must be non-empty."""
        proj = self._load(project_id)
        accumulated_code = ""
        for step in proj["steps"]:
            if accumulated_code:
                accumulated_code += "\n" + step["solution"]
            else:
                accumulated_code = step["solution"]

            if re.search(r"\binput\s*\(", accumulated_code):
                assert len(step.get("mock_inputs", [])) > 0, (
                    f"Step {step['step_num']}: accumulated code has input() but mock_inputs is empty"
                )


def test_no_duplicate_project_ids():
    """No two project files should have the same id field."""
    seen_ids = {}
    for path in get_project_files():
        proj = load_project(path)
        pid = proj["id"]
        assert pid not in seen_ids, (
            f"Duplicate project id '{pid}' in {path.name} and {seen_ids[pid]}"
        )
        seen_ids[pid] = path.name
