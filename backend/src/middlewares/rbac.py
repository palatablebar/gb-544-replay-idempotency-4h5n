"""RBAC：require_role(*roles) 与 require_pipeline_access(action) 依赖工厂。"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants import error_codes as codes
from src.constants.roles import ROLE_OWNER, role_can
from src.middlewares.auth import get_current_user
from src.models.sync_pipeline import SyncPipeline
from src.models.user import User
from src.utils.errors import AppError


def require_role(*roles: str) -> Callable[..., User]:
    allowed = tuple(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise AppError(
                codes.FORBIDDEN,
                f"当前角色（{user.role}）无权执行该操作",
                f"role={user.role} required={allowed}",
            )
        return user

    return dependency


def require_permission(action: str) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_can(user.role, action):
            raise AppError(
                codes.FORBIDDEN,
                f"当前角色（{user.role}）无 {action} 权限",
                f"role={user.role} action={action}",
            )
        return user

    return dependency


def require_pipeline_access(action: str) -> Callable[..., Any]:
    """同时校验角色与 owner 归属：非 owner 只能操作自己名下的管道写入动作。"""

    def dependency(
        pipeline_id: str,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Any:
        if not role_can(user.role, action):
            raise AppError(
                codes.FORBIDDEN,
                f"当前角色（{user.role}）无 {action} 权限",
                f"role={user.role} action={action}",
            )
        pipeline = db.get(SyncPipeline, pipeline_id)
        if pipeline is None:
            raise AppError(codes.NOT_FOUND, "管道不存在", f"pipeline_id={pipeline_id}")
        if user.role != ROLE_OWNER and str(pipeline.owner_id) != str(user.id):
            raise AppError(
                codes.FORBIDDEN,
                "只能操作自己名下的管道",
                f"pipeline={pipeline_id} owner={pipeline.owner_id} user={user.id}",
            )
        return pipeline

    return dependency
