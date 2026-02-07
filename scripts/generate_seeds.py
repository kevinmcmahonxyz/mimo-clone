"""Generate seed projects for all 9 levels × 3 tiers.
Validates each project by executing the full solution before saving.

Usage: python -m scripts.generate_seeds
"""

import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.services.claude_service import generate_project
from backend.sandbox.executor import execute_code

LESSONS = json.loads(Path("data/lessons.json").read_text())
PROJECTS_DIR = Path("data/projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_RETRIES = 3


def fix_cumulative_solutions(project_data: dict):
    steps = project_data.get("steps", [])
    if len(steps) < 2:
        return
    prev_lines = []
    for step in steps:
        sol = step.get("solution", "")
        sol_lines = sol.split("\n")
        if len(sol_lines) > len(prev_lines) and prev_lines:
            if all(sol_lines[i] == prev_lines[i] for i in range(len(prev_lines))):
                step["solution"] = "\n".join(sol_lines[len(prev_lines):])
        prev_lines = sol_lines


def generate_and_validate(level_id: int, tier: int, concepts: list[str]) -> dict | None:
    tier_names = {1: "basic", 2: "intermediate", 3: "capstone"}
    print(f"  Generating Level {level_id} / {tier_names[tier]}...", end=" ", flush=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            project = generate_project(
                level_id=level_id,
                tier=tier,
                concepts=concepts,
            )
            if not project:
                print(f"(empty response, retry {attempt})", end=" ", flush=True)
                continue

            fix_cumulative_solutions(project)

            # Rebuild full_solution from steps
            project["full_solution"] = "\n".join(
                step["solution"] for step in project["steps"]
            )
            project["is_generated"] = False  # Treat seeds as hand-crafted

            # Validate by executing
            last_step = project["steps"][-1] if project["steps"] else {}
            mock_inputs = last_step.get("mock_inputs", [])
            result = execute_code(project["full_solution"], mock_inputs)

            if result["success"]:
                print(f"OK ({len(project['steps'])} steps)")
                return project
            else:
                print(f"(code error, retry {attempt}): {result['error'][:60]}", end=" ", flush=True)

        except Exception as e:
            print(f"(exception, retry {attempt}): {str(e)[:60]}", end=" ", flush=True)

        time.sleep(1)

    print("FAILED after retries")
    return None


def main():
    if not settings.claude_api_key:
        print("Error: MIMO_CLAUDE_API_KEY not set in .env")
        sys.exit(1)

    existing = {p.stem for p in PROJECTS_DIR.glob("*.json")}
    print(f"Found {len(existing)} existing projects: {sorted(existing)}")
    print()

    generated = 0
    failed = 0

    for lesson in LESSONS:
        level_id = lesson["id"]
        concepts = lesson["concepts"]
        print(f"Level {level_id}: {lesson['name']}")

        for tier in [1, 2, 3]:
            # Check if any project exists for this level/tier
            tier_names = {1: "basic", 2: "intermediate", 3: "capstone"}
            prefix = f"level{level_id}_{tier_names[tier]}"
            if any(e.startswith(prefix) for e in existing):
                print(f"  Skipping {prefix} (already exists)")
                continue

            project = generate_and_validate(level_id, tier, concepts)
            if project:
                # Normalize the ID
                project["id"] = f"level{level_id}_{tier_names[tier]}_{project['id'].split('_')[-1]}"
                filename = f"{project['id']}.json"
                filepath = PROJECTS_DIR / filename
                filepath.write_text(json.dumps(project, indent=2))
                print(f"    Saved: {filename}")
                generated += 1
            else:
                failed += 1

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        print()

    print(f"Done. Generated: {generated}, Failed: {failed}")


if __name__ == "__main__":
    main()
