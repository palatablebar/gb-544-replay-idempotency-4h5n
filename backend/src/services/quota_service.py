"""并发配额：统计 status in (queued, running) 的运行数。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import RunStatus
from src.models.sync_run import SyncRun
from src.models.user import User
from src.utils.errors import AppError

ACTIVE_STATUSES = (RunStatus.QUEUED.value, RunStatus.RUNNING.value)


def active_count(db: Session, user_id: Any | None = None) -> int:
    query = db.query(SyncRun).filter(SyncRun.status.in_(ACTIVE_STATUSES))
    if user_id is not None:
        query = query.filter(SyncRun.triggered_by == user_id)
    return query.count()


def summary(db: Session, user: User) -> dict[str, Any]:
    used = active_count(db, user.id)
    maximum = int(user.max_concurrent_runs or 2)
    return {
        "max": maximum,
        "active": used,
        "remaining": max(maximum - used, 0),
        "global_active": active_count(db),
        "statuses": list(ACTIVE_STATUSES),
    }


def check_quota(db: Session, user: User) -> None:
    used = active_count(db, user.id)
    maximum = int(user.max_concurrent_runs or 2)
    if used >= maximum:
        raise AppError(
            codes.RUN_QUOTA_EXCEEDED,
            f"并发运行数已达上限（{used}/{maximum}），请稍后再试",
            f"user={user.id} active={used} max={maximum}",
            extra={"active": used, "max": maximum},
        )
