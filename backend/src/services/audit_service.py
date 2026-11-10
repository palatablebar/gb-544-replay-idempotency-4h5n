"""审计落库：写入失败绝不影响主流程（try/except + WARNING）。"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import ActorKind
from src.constants.log_templates import LOG_TEMPLATES  # noqa: F401 - 证明模板集中
from src.models.audit_log import AuditLog
from src.utils.logger import get_logger

logger = get_logger("syncmesh.audit")


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    actor_id: str | None = None,
    actor_kind: str = ActorKind.USER.value,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    trace_id: str | None = None,
) -> None:
    try:
        db.add(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None,
                actor_id=actor_id,
                actor_kind=actor_kind,
                payload_json=payload or {},
                ip=ip,
                trace_id=trace_id,
            )
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning(
            "audit write failed action=%s error=%s", action, exc, exc_info=False
        )


def list_audit(db: Session, entity_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = db.query(AuditLog)
    if entity_id:
        query = query.filter(AuditLog.entity_id == str(entity_id))
    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(row.id),
            "action": row.action,
            "actor_kind": row.actor_kind,
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "payload": row.payload_json,
            "ip": row.ip,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
