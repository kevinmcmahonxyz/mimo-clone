from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.storage.database import init_db, seed_lessons, seed_projects
from backend.api.lessons import router as lessons_router
from backend.api.projects import router as projects_router
from backend.api.execution import router as execution_router
from backend.api.generation import router as generation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_lessons()
    seed_projects()
    yield


app = FastAPI(title="Mimo Clone", version="1.0.0", lifespan=lifespan)

# API routes
app.include_router(lessons_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")

# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_dir / "index.html"))
