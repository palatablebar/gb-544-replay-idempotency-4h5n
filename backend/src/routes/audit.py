from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    entity_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    return audit_controller.list_audit(entity_id, limit, db, user)
