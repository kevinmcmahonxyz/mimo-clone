from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from backend.storage.database import get_session
from backend.services.execution_service import run_and_validate

router = APIRouter(tags=["execution"])


class ExecuteRequest(BaseModel):
    project_id: str
    step_num: int
    code: str
    accumulated_code: str = ""


@router.post("/execute")
def execute_code(req: ExecuteRequest, session: Session = Depends(get_session)):
    result = run_and_validate(
        project_id=req.project_id,
        step_num=req.step_num,
        code=req.code,
        accumulated_code=req.accumulated_code,
        session=session,
    )
    return result
