from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import api_key_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("")
def list_keys(db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return api_key_controller.list_keys(db, user)


@router.post("")
def create_key(payload: api_key_controller.ApiKeyCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("apikeys:write"))) -> dict:
    return api_key_controller.create_key(payload, request, db, user)


@router.delete("/{key_id}")
def revoke_key(key_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("apikeys:write"))) -> dict:
    return api_key_controller.revoke_key(key_id, request, db, user)
