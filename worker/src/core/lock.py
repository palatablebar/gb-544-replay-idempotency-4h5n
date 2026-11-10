"""管道锁：DB pipeline_locks（唯一键 + locked_until） + Redis 短期标记。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.models.pipeline_lock import PipelineLock
from src.utils.logger import get_logger
from worker_src.constants.tuning import LOCK_TTL_SECONDS

logger = get_logger("syncmesh.worker.lock")


def acquire(db: Session, pipeline_id: Any, run_id: Any) -> bool:
    now = datetime.now(timezone.utc)
    existing = db.query(PipelineLock).filter(PipelineLock.pipeline_id == pipeline_id).one_or_none()
    if existing is None:
        db.add(
            PipelineLock(
                pipeline_id=pipeline_id,
                run_id=run_id,
                locked_until=now + timedelta(seconds=LOCK_TTL_SECONDS),
                locked_by=f"worker:{run_id}",
                created_at=now,
            )
        )
        db.commit()
        return True
    if existing.locked_until and existing.locked_until.replace(tzinfo=timezone.utc) > now:
        if str(existing.run_id) != str(run_id):
            logger.warning(
                "lock conflict pipeline=%s held_by_run=%s", pipeline_id, existing.run_id
            )
            return False
    existing.run_id = run_id
    existing.locked_until = now + timedelta(seconds=LOCK_TTL_SECONDS)
    existing.locked_by = f"worker:{run_id}"
    db.commit()
    return True


def release(db: Session, pipeline_id: Any, run_id: Any) -> None:
    existing = db.query(PipelineLock).filter(PipelineLock.pipeline_id == pipeline_id).one_or_none()
    if existing is None:
        return
    if str(existing.run_id) != str(run_id):
        return
    db.delete(existing)
    db.commit()


def refresh(db: Session, pipeline_id: Any, run_id: Any) -> None:
    existing = db.query(PipelineLock).filter(PipelineLock.pipeline_id == pipeline_id).one_or_none()
    if existing is None or str(existing.run_id) != str(run_id):
        return
    existing.locked_until = datetime.now(timezone.utc) + timedelta(seconds=LOCK_TTL_SECONDS)
    db.commit()
