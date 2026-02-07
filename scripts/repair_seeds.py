"""Run the repair pipeline on existing seed projects without regenerating.

Loads each project JSON, checks for quality issues, applies programmatic
auto-fix and (if needed) Claude repair, then saves back to disk.

Usage:
  python -m scripts.repair_seeds              # Repair all projects with issues
  python -m scripts.repair_seeds --dry-run    # Show what would be fixed, don't save
  python -m scripts.repair_seeds --level 1    # Only repair level 1 projects
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.quality import validate_project_quality, fix_cumulative_solutions
from backend.services.repair_service import auto_fix_project, claude_repair_project

PROJECTS_DIR = Path("data/projects")


def main():
    parser = argparse.ArgumentParser(description="Repair existing seed projects")
    parser.add_argument("--dry-run", action="store_true", help="Show issues without fixing")
    parser.add_argument("--level", type=int, nargs="+", help="Only repair these level(s)")
    args = parser.parse_args()

    project_files = sorted(PROJECTS_DIR.glob("*.json"))
    if args.level:
        project_files = [
            p for p in project_files
            if any(p.stem.startswith(f"level{l}_") for l in args.level)
        ]

    print(f"Checking {len(project_files)} projects...\n")

    clean = 0
    auto_fixed = 0
    claude_fixed = 0
    still_broken = 0

    for path in project_files:
        project = json.loads(path.read_text())
        errors = validate_project_quality(project)

        if not errors:
            clean += 1
            continue

        print(f"{path.stem}: {len(errors)} issue(s)")
        for err in errors:
            print(f"  - {err}")

        if args.dry_run:
            print()
            still_broken += 1
            continue

        # Phase 1: programmatic fixes
        project, remaining = auto_fix_project(project, errors)
        if not remaining:
            # Rebuild full_solution after fixes
            project["full_solution"] = "\n".join(
                step["solution"] for step in project["steps"]
            )
            path.write_text(json.dumps(project, indent=2))
            print(f"  -> Auto-fixed!\n")
            auto_fixed += 1
            continue

        print(f"  -> {len(remaining)} issue(s) remain after auto-fix")

        # Phase 2: up to 2 Claude repair attempts
        for attempt in range(2):
            print(f"  -> Claude repair attempt {attempt + 1}...", end=" ", flush=True)
            repaired = claude_repair_project(project, remaining)
            if not repaired:
                print("failed (no response)")
                break
            project = repaired
            remaining = validate_project_quality(project)
            if not remaining:
                print("success!")
                break
            print(f"{len(remaining)} issue(s) remain")

        if not remaining:
            project["full_solution"] = "\n".join(
                step["solution"] for step in project["steps"]
            )
            path.write_text(json.dumps(project, indent=2))
            print(f"  -> Claude-fixed!\n")
            claude_fixed += 1
        else:
            print(f"  -> Still broken after repair:")
            for err in remaining[:3]:
                print(f"     - {err}")
            print()
            still_broken += 1

    print(f"Results: {clean} clean, {auto_fixed} auto-fixed, {claude_fixed} claude-fixed, {still_broken} still broken")


if __name__ == "__main__":
    main()
