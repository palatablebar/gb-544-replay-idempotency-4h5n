from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import rejected_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission

router = APIRouter(tags=["rejected"])


@router.get("/runs/{run_id}/rejected")
def list_rejected(
    run_id: str,
    reason_code: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    return rejected_controller.list_rejected(run_id, reason_code, page, page_size, db, user)


@router.get("/runs/{run_id}/rejected/export")
def export_rejected(run_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)) -> Response:
    return rejected_controller.export_rejected(run_id, db, user)


@router.post("/rejected/{rejected_id}/replay")
def replay_one(rejected_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("runs:replay"))) -> dict:
    return rejected_controller.replay_one(rejected_id, request, db, user)
