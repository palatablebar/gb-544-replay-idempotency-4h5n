"""认证 controller：登录 / 刷新 / me / 改并发上限。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.enums import ActorKind
from src.constants.roles import ROLE_OWNER, ROLE_LABELS
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_role
from src.models.user import User
from src.schemas.auth import LoginRequest, RefreshRequest, UserUpdateRequest, serialize_user
from src.services import audit_service, auth_service, quota_service
from src.utils.errors import AppError
from src.utils.logger import get_logger

logger = get_logger("syncmesh.auth.controller")


def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = auth_service.authenticate(db, payload.email, payload.password)
    tokens = auth_service.issue_tokens(user)
    audit_service.record(
        db,
        action="auth.login",
        entity_type="User",
        entity_id=str(user.id),
        actor_id=str(user.id),
        payload={"role": user.role},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return {**tokens, "user": serialize_user(user)}


def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    tokens = auth_service.refresh(db, payload.refresh_token)
    return tokens


def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    payload = serialize_user(user)
    payload["role_label"] = ROLE_LABELS.get(user.role, user.role)
    payload["quota"] = quota_service.summary(db, user)
    return payload


def list_users(user: User = Depends(require_role(ROLE_OWNER)), db: Session = Depends(get_db)) -> dict:
    users = db.query(User).order_by(User.created_at.asc()).all()
    return {"items": [serialize_user(row) for row in users]}


def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    request: Request,
    user: User = Depends(require_role(ROLE_OWNER)),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(User, user_id)
    if target is None:
        raise AppError("NOT_FOUND", "用户不存在", f"user_id={user_id}")
    if payload.display_name is not None:
        target.display_name = payload.display_name
    if payload.max_concurrent_runs is not None:
        target.max_concurrent_runs = payload.max_concurrent_runs
    if payload.is_active is not None and str(target.id) != str(user.id):
        target.is_active = payload.is_active
    db.commit()
    audit_service.record(
        db,
        action="user.update",
        entity_type="User",
        entity_id=str(target.id),
        actor_id=str(user.id),
        actor_kind=ActorKind.USER.value,
        payload=payload.model_dump(exclude_none=True),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_user(target)
