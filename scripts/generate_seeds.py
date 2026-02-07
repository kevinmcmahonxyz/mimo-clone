"""Generate seed projects for all 9 levels x 3 tiers.
Validates each project by executing the full solution AND running quality checks before saving.

Usage:
  python -m scripts.generate_seeds              # Generate all missing projects
  python -m scripts.generate_seeds --level 1    # Generate only Level 1
  python -m scripts.generate_seeds --level 2 3  # Generate Levels 2 and 3
  python -m scripts.generate_seeds --level 1 --tier 2  # Level 1, Intermediate only
  python -m scripts.generate_seeds --tier 1      # Basic tier across all levels
  python -m scripts.generate_seeds --force       # Regenerate even if files exist
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.services.claude_service import generate_project
from backend.services.repair_service import auto_fix_project, claude_repair_project
from backend.quality import fix_cumulative_solutions, validate_project_quality
from backend.sandbox.executor import execute_code

LESSONS = json.loads(Path("data/lessons.json").read_text())
PROJECTS_DIR = Path("data/projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_RETRIES = 3

TIER_NAMES = {1: "basic", 2: "intermediate", 3: "capstone"}


def generate_and_validate(level_id: int, tier: int, concepts: list[str]) -> dict | None:
    print(f"  Generating Level {level_id} / {TIER_NAMES[tier]}...", end=" ", flush=True)

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

            # Validate: execute full solution
            last_step = project["steps"][-1] if project["steps"] else {}
            mock_inputs = last_step.get("mock_inputs", [])
            result = execute_code(project["full_solution"], mock_inputs)

            if not result["success"]:
                print(f"(code error, retry {attempt}): {result['error'][:60]}", end=" ", flush=True)
                time.sleep(1)
                continue

            # Quality checks
            quality_errors = validate_project_quality(project)
            if not quality_errors:
                print(f"OK ({len(project['steps'])} steps)")
                return project

            # Phase 1: programmatic fixes
            print(f"(repairing, attempt {attempt})...", end=" ", flush=True)
            project, remaining = auto_fix_project(project, quality_errors)

            # Phase 2: up to 2 Claude repair attempts
            for repair_attempt in range(2):
                if not remaining:
                    break
                print(f"(claude repair {repair_attempt + 1})...", end=" ", flush=True)
                repaired = claude_repair_project(project, remaining)
                if not repaired:
                    break
                project = repaired
                remaining = validate_project_quality(project)

            if not remaining:
                print(f"OK — repaired ({len(project['steps'])} steps)")
                return project

            # Still broken — log errors and fall through to full regen
            print(f"(repair failed, retry {attempt}):", flush=True)
            for err in remaining[:3]:
                print(f"    - {err}")
            time.sleep(1)

        except Exception as e:
            print(f"(exception, retry {attempt}): {str(e)[:60]}", end=" ", flush=True)

        time.sleep(1)

    print("FAILED after retries")
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate seed projects")
    parser.add_argument(
        "--level", type=int, nargs="+",
        help="Only generate for these level(s), e.g. --level 1 2 3"
    )
    parser.add_argument(
        "--tier", type=int, nargs="+", choices=[1, 2, 3],
        help="Only generate these tier(s), e.g. --tier 1 2"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate even if project file already exists"
    )
    args = parser.parse_args()

    if not settings.claude_api_key:
        print("Error: MIMO_CLAUDE_API_KEY not set in .env")
        sys.exit(1)

    # Filter lessons by --level
    lessons = LESSONS
    if args.level:
        lessons = [l for l in LESSONS if l["id"] in args.level]
        if not lessons:
            print(f"Error: no lessons found for level(s) {args.level}")
            sys.exit(1)

    # Filter tiers
    tiers = args.tier or [1, 2, 3]

    existing = {p.stem for p in PROJECTS_DIR.glob("*.json")}

    level_ids = [l["id"] for l in lessons]
    tier_labels = [TIER_NAMES[t] for t in tiers]
    print(f"Levels: {level_ids}")
    print(f"Tiers:  {tier_labels}")
    print(f"Force:  {args.force}")
    print(f"Found {len(existing)} existing project files")
    print()

    generated = 0
    failed = 0
    skipped = 0

    for lesson in lessons:
        level_id = lesson["id"]
        concepts = lesson["concepts"]
        print(f"Level {level_id}: {lesson['name']}")

        for tier in tiers:
            prefix = f"level{level_id}_{TIER_NAMES[tier]}"
            if not args.force and any(e.startswith(prefix) for e in existing):
                print(f"  Skipping {prefix} (already exists)")
                skipped += 1
                continue

            project = generate_and_validate(level_id, tier, concepts)
            if project:
                project["id"] = f"level{level_id}_{TIER_NAMES[tier]}_{project['id'].split('_')[-1]}"
                filename = f"{project['id']}.json"
                filepath = PROJECTS_DIR / filename

                # If --force, remove old file first
                if args.force:
                    for old in PROJECTS_DIR.glob(f"{prefix}*.json"):
                        old.unlink()
                        print(f"    Removed: {old.name}")

                filepath.write_text(json.dumps(project, indent=2))
                print(f"    Saved: {filename}")
                generated += 1
            else:
                failed += 1

            time.sleep(0.5)

        print()

    print(f"Done. Generated: {generated}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
