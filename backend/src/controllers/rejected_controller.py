"""拒绝记录 controller：分页、按原因过滤、导出 JSONL、单条重放。"""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.rejected_record import RejectedRecord
from src.models.user import User
from src.schemas.rejected import serialize_rejected
from src.schemas.run import ReplayRequest
from src.services import audit_service, run_service
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger

logger = get_logger("syncmesh.rejected.controller")


def list_rejected(
    run_id: str,
    reason_code: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(RejectedRecord).filter(RejectedRecord.run_id == run_id)
    if reason_code:
        query = query.filter(RejectedRecord.reason_code == reason_code)
    total = query.count()
    rows = (
        query.order_by(RejectedRecord.source_row_index.asc())
        .limit(min(page_size, 200))
        .offset(max(page - 1, 0) * page_size)
        .all()
    )
    grouped: dict[str, int] = {}
    for row in db.query(RejectedRecord).filter(RejectedRecord.run_id == run_id).all():
        grouped[row.reason_code] = grouped.get(row.reason_code, 0) + 1
    return {
        "items": [serialize_rejected(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "by_reason": grouped,
    }


def export_rejected(run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    rows = (
        db.query(RejectedRecord)
        .filter(RejectedRecord.run_id == run_id)
        .order_by(RejectedRecord.source_row_index.asc())
        .all()
    )
    body = "\n".join(json.dumps(serialize_rejected(row), ensure_ascii=False) for row in rows)
    return Response(
        content=body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="rejected-{run_id}.jsonl"'},
    )


def replay_one(
    rejected_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("runs:replay")),
) -> dict:
    try:
        record = db.get(RejectedRecord, UUID(str(rejected_id)))
    except ValueError:
        raise not_found("RejectedRecord", rejected_id)
    if record is None:
        raise not_found("RejectedRecord", rejected_id)
    run = run_service.get_run(db, record.run_id)
    result = run_service.replay_records(
        db, run=run, rejected_ids=[str(record.id)], reason_code=None, actor=user
    )
    audit_service.record(
        db,
        action="rejected.replay",
        entity_type="RejectedRecord",
        entity_id=str(record.id),
        actor_id=str(user.id),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return result
