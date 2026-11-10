"""审计 controller：按实体查操作记录。"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.services import audit_service


def list_audit(
    entity_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return {"items": audit_service.list_audit(db, entity_id=entity_id, limit=min(limit, 200))}
