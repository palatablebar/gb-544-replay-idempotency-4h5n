"""RBAC 角色常量。前后端必须一致：users.role / constants/roles.py / frontend constants / <RequireRole>。"""
from __future__ import annotations

ROLE_OWNER = "owner"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

ALL_ROLES: tuple[str, ...] = (ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER)

# 能力矩阵：action -> 允许的角色
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "sources:read": ALL_ROLES,
    "sources:write": (ROLE_OWNER,),
    "pipelines:read": ALL_ROLES,
    "pipelines:write": (ROLE_OWNER,),
    "pipelines:delete": (ROLE_OWNER,),
    "mappings:write": (ROLE_OWNER, ROLE_OPERATOR),
    "runs:read": ALL_ROLES,
    "runs:trigger": (ROLE_OWNER, ROLE_OPERATOR),
    "runs:replay": (ROLE_OWNER, ROLE_OPERATOR),
    "targets:read": ALL_ROLES,
    "apikeys:write": (ROLE_OWNER,),
    "users:admin": (ROLE_OWNER,),
    "audit:read": ALL_ROLES,
}


def role_can(role: str, action: str) -> bool:
    return role in PERMISSIONS.get(action, ())


ROLE_LABELS = {ROLE_OWNER: "数据工程师", ROLE_OPERATOR: "分析师", ROLE_VIEWER: "BI"}
