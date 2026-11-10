"""API Key 签发 / 校验 / 吊销：库中只存 hash 与前缀。"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.models.api_key import ApiKey
from src.utils.errors import AppError

DEFAULT_SCOPES = ["runs:trigger", "runs:replay"]
KEY_PREFIX_LEN = 10


def _hash(raw_key: str) -> str:
    return hashlib.sha256(f"{settings.api_key_pepper}:{raw_key}".encode()).hexdigest()


def issue(db: Session, *, user_id: Any, name: str, scopes: list[str] | None = None) -> tuple[ApiKey, str]:
    raw_key = f"smk_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:KEY_PREFIX_LEN]
    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_prefix=prefix,
        key_hash=_hash(raw_key),
        scopes=scopes or DEFAULT_SCOPES,
        created_at=datetime.now(timezone.utc),
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def verify(db: Session, raw_key: str, required_scope: str | None = None) -> ApiKey:
    if not raw_key or not raw_key.startswith("smk_"):
        raise AppError(codes.API_KEY_INVALID, "API Key 无效或已吊销", "malformed key")
    prefix = raw_key[:KEY_PREFIX_LEN]
    api_key = db.query(ApiKey).filter(ApiKey.key_prefix == prefix).one_or_none()
    if api_key is None or api_key.revoked_at is not None:
        raise AppError(codes.API_KEY_INVALID, "API Key 无效或已吊销", "key not found or revoked")
    if api_key.key_hash != _hash(raw_key):
        raise AppError(codes.API_KEY_INVALID, "API Key 无效或已吊销", "hash mismatch")
    if required_scope and required_scope not in (api_key.scopes or []):
        raise AppError(
            codes.API_KEY_SCOPE_DENIED,
            f"该 API Key 缺少 scope {required_scope}",
            f"scopes={api_key.scopes}",
        )
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key


def revoke(db: Session, key_id: Any, user_id: Any) -> None:
    api_key = db.get(ApiKey, key_id)
    if api_key is None or str(api_key.user_id) != str(user_id):
        raise AppError(codes.NOT_FOUND, "API Key 不存在", f"key_id={key_id}")
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()


def list_keys(db: Session, user_id: Any) -> list[dict[str, Any]]:
    keys = db.query(ApiKey).filter(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc()).all()
    return [
        {
            "id": str(key.id),
            "name": key.name,
            "key_prefix": f"{key.key_prefix}…",
            "scopes": key.scopes or [],
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
        }
        for key in keys
    ]
