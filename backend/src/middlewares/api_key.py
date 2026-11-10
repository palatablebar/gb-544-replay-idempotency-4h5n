"""X-API-Key 中间件依赖：仅挂在 /runs/trigger 与 /runs/{id}/replay 上。"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants import error_codes as codes
from src.models.user import User
from src.services import api_key_service
from src.utils.errors import AppError


class ApiActor:
    def __init__(self, user: User | None, api_key: Any | None, actor_kind: str) -> None:
        self.user = user
        self.api_key = api_key
        self.actor_kind = actor_kind

    @property
    def user_id(self) -> Any:
        return getattr(self.user, "id", None)


def api_actor(
    request: Request,
    required_scope: str = "runs:trigger",
    db: Session = Depends(get_db),
) -> ApiActor:
    raw_key = request.headers.get("x-api-key")
    if not raw_key:
        raise AppError(codes.API_KEY_INVALID, "缺少 X-API-Key 头", "x-api-key empty")
    api_key = api_key_service.verify(db, raw_key, required_scope=required_scope)
    user = db.get(User, api_key.user_id)
    if user is None or not user.is_active:
        raise AppError(codes.API_KEY_INVALID, "API Key 关联账号不可用", f"key={api_key.id}")
    request.state.actor_kind = "api_key"
    request.state.api_key_id = str(api_key.id)
    return ApiActor(user=user, api_key=api_key, actor_kind="api_key")


def trigger_actor(request: Request, db: Session = Depends(get_db)) -> ApiActor:
    return api_actor(request, required_scope="runs:trigger", db=db)


def replay_actor(request: Request, db: Session = Depends(get_db)) -> ApiActor:
    return api_actor(request, required_scope="runs:replay", db=db)
