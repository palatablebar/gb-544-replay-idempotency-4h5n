"""API Key controller：签发（只回显一次）、列表、吊销。"""
from __future__ import annotations

from fastapi import Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.enums import ActorKind
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.services import api_key_service, audit_service


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = ["runs:trigger", "runs:replay"]


def list_keys(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return {"items": api_key_service.list_keys(db, user.id)}


def create_key(
    payload: ApiKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("apikeys:write")),
) -> dict:
    api_key, raw_key = api_key_service.issue(
        db, user_id=user.id, name=payload.name, scopes=payload.scopes
    )
    audit_service.record(
        db,
        action="apikey.issue",
        entity_type="ApiKey",
        entity_id=str(api_key.id),
        actor_id=str(user.id),
        actor_kind=ActorKind.USER.value,
        payload={"name": api_key.name, "scopes": api_key.scopes},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "scopes": api_key.scopes,
        "plaintext": raw_key,
        "notice": "明文只返回这一次，请立刻保存",
    }


def revoke_key(
    key_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("apikeys:write")),
) -> dict:
    api_key_service.revoke(db, key_id, user.id)
    audit_service.record(
        db,
        action="apikey.revoke",
        entity_type="ApiKey",
        entity_id=str(key_id),
        actor_id=str(user.id),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return {"ok": True}
