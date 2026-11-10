"""过期 staging 表与过期管道锁清理。"""
from __future__ import annotations

from datetime import datetime, timezone

from src.config.database import session_scope
from src.models.pipeline_lock import PipelineLock
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app
from worker_src.constants.tuning import STAGING_TTL_HOURS
from worker_src.core import storage

logger = get_logger("syncmesh.worker.cleanup")


@celery_app.task(name="syncmesh.cleanup_staging")
def cleanup_staging() -> dict:
    dropped = storage.drop_stale_staging(STAGING_TTL_HOURS)
    expired_locks = 0
    with session_scope() as db:
        now = datetime.now(timezone.utc)
        for lock_row in db.query(PipelineLock).all():
            locked_until = lock_row.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until < now:
                db.delete(lock_row)
                expired_locks += 1
        db.commit()
    logger.info("cleanup staging dropped=%s expired_locks=%s", len(dropped), expired_locks)
    return {"dropped": dropped, "expired_locks": expired_locks}
