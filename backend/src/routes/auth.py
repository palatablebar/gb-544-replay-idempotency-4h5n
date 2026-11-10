from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import auth_controller
from src.middlewares.rbac import require_role
from src.constants.roles import ROLE_OWNER

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, payload: auth_controller.LoginRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.login(request, payload, db)


@router.post("/refresh")
def refresh(payload: auth_controller.RefreshRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.refresh(payload, db)


@router.get("/me")
def me(user=Depends(auth_controller.get_current_user), db: Session = Depends(get_db)) -> dict:
    return auth_controller.me(user, db)


@router.get("/users")
def list_users(user=Depends(require_role(ROLE_OWNER)), db: Session = Depends(get_db)) -> dict:
    return auth_controller.list_users(user, db)


@router.patch("/users/{user_id}")
def update_user(
    user_id: str, payload: auth_controller.UserUpdateRequest, request: Request,
    user=Depends(require_role(ROLE_OWNER)), db: Session = Depends(get_db),
) -> dict:
    return auth_controller.update_user(user_id, payload, request, user, db)
