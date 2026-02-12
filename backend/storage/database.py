import json
from pathlib import Path
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from datetime import datetime

from backend.config import settings


# --- Models ---

class Lesson(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    description: str
    generation_context: Optional[str] = None
    concepts: str  # JSON list
    examples: str  # JSON list
    prerequisite_id: Optional[int] = None

    @property
    def concepts_list(self) -> list[str]:
        return json.loads(self.concepts)

    @property
    def examples_list(self) -> list[str]:
        return json.loads(self.examples)


class Project(SQLModel, table=True):
    id: str = Field(primary_key=True)
    level_id: int = Field(index=True)
    tier: int = Field(index=True)  # 1=basic, 2=intermediate, 3=capstone
    name: str
    description: str
    learning_goals: str  # JSON list
    concepts_used: str  # JSON list
    total_lines: int
    steps: str  # JSON list of step objects
    full_solution: str
    difficulty_rating: int = 1
    estimated_minutes: int = 10
    is_generated: bool = False


class Progress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="default", index=True)
    project_id: str = Field(index=True)
    step_num: int
    completed: bool = False
    completed_at: Optional[str] = None
    code: str = ""


# --- Database setup ---

DB_DIR = Path("data/db")
DB_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_DIR}/mimo.db", echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def seed_lessons():
    """Seed lessons from data/lessons.json if table is empty."""
    with Session(engine) as session:
        existing = session.exec(select(Lesson)).first()
        if existing:
            return

        lessons_file = Path("data/lessons.json")
        if not lessons_file.exists():
            return

        lessons_data = json.loads(lessons_file.read_text())
        for item in lessons_data:
            lesson = Lesson(
                id=item["id"],
                name=item["name"],
                description=item["description"],
                generation_context=item.get("generation_context"),
                concepts=json.dumps(item["concepts"]),
                examples=json.dumps(item["examples"]),
                prerequisite_id=item.get("prerequisite_id"),
            )
            session.add(lesson)
        session.commit()


def seed_projects():
    """Seed projects from data/projects/*.json if table is empty."""
    with Session(engine) as session:
        existing = session.exec(select(Project)).first()
        if existing:
            return

        projects_dir = Path("data/projects")
        if not projects_dir.exists():
            return

        for pfile in sorted(projects_dir.glob("*.json")):
            data = json.loads(pfile.read_text())
            project = Project(
                id=data["id"],
                level_id=data["level_id"],
                tier=data["tier"],
                name=data["name"],
                description=data["description"],
                learning_goals=json.dumps(data["learning_goals"]),
                concepts_used=json.dumps(data["concepts_used"]),
                total_lines=data["total_lines"],
                steps=json.dumps(data["steps"]),
                full_solution=data["full_solution"],
                difficulty_rating=data.get("difficulty_rating", 1),
                estimated_minutes=data.get("estimated_minutes", 10),
                is_generated=data.get("is_generated", False),
            )
            session.add(project)
        session.commit()
