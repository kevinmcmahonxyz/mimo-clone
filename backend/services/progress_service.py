import json
from sqlmodel import Session, select

from backend.storage.database import Progress, Project


def get_user_progress(user_id: str, session: Session) -> dict:
    """Get comprehensive progress for a user."""
    progress_records = session.exec(
        select(Progress).where(Progress.user_id == user_id)
    ).all()

    # Group by project
    projects_progress = {}
    for p in progress_records:
        if p.project_id not in projects_progress:
            projects_progress[p.project_id] = {
                "project_id": p.project_id,
                "steps_completed": [],
                "is_complete": False,
            }
        if p.completed:
            projects_progress[p.project_id]["steps_completed"].append(p.step_num)

    # Check if projects are fully complete
    for pid, pp in projects_progress.items():
        project = session.get(Project, pid)
        if project:
            steps = json.loads(project.steps)
            total_steps = len(steps)
            pp["total_steps"] = total_steps
            pp["is_complete"] = len(pp["steps_completed"]) >= total_steps

    # Calculate level completion
    all_projects = session.exec(select(Project)).all()
    levels_status = {}
    for proj in all_projects:
        if proj.level_id not in levels_status:
            levels_status[proj.level_id] = {"tiers": {}}
        pp = projects_progress.get(proj.id, {})
        levels_status[proj.level_id]["tiers"][proj.tier] = pp.get("is_complete", False)

    return {
        "projects": projects_progress,
        "levels": levels_status,
    }


def is_tier_unlocked(level_id: int, tier: int, user_id: str, session: Session) -> bool:
    """Check if a tier is unlocked for a user."""
    if level_id == 1 and tier == 1:
        return True  # Always unlocked

    if tier == 1:
        # Check if previous level's capstone is complete
        prev_projects = session.exec(
            select(Project).where(
                Project.level_id == level_id - 1, Project.tier == 3
            )
        ).all()
        if not prev_projects:
            # If no capstone, check if any project at prev level is complete
            prev_projects = session.exec(
                select(Project).where(Project.level_id == level_id - 1)
            ).all()

        for proj in prev_projects:
            progress = session.exec(
                select(Progress).where(
                    Progress.user_id == user_id,
                    Progress.project_id == proj.id,
                    Progress.completed == True,
                )
            ).all()
            steps = json.loads(proj.steps)
            if len(progress) >= len(steps):
                return True
        return False

    # Tier 2 needs tier 1 complete; tier 3 needs tier 2 complete
    prev_tier_projects = session.exec(
        select(Project).where(
            Project.level_id == level_id, Project.tier == tier - 1
        )
    ).all()
    for proj in prev_tier_projects:
        progress = session.exec(
            select(Progress).where(
                Progress.user_id == user_id,
                Progress.project_id == proj.id,
                Progress.completed == True,
            )
        ).all()
        steps = json.loads(proj.steps)
        if len(progress) >= len(steps):
            return True
    return False
