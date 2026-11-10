"""cron 到期扫描：beat 每 SCHEDULER_POLL_SECONDS 触发一次。"""
from __future__ import annotations

from src.config.database import session_scope
from src.constants.enums import TriggerType
from src.models.user import User
from src.services import run_service, scheduler_service
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app

logger = get_logger("syncmesh.worker.schedule")


@celery_app.task(name="syncmesh.scan_schedules")
def scan_schedules() -> dict:
    enqueued = 0
    checked = 0
    with session_scope() as db:
        due = scheduler_service.scan_due_pipelines(db)
        checked = len(due)
        for pipeline in due:
            owner = db.get(User, pipeline.owner_id)
            if owner is None:
                continue
            try:
                run_service.create_run(
                    db, pipeline=pipeline, user=owner,
                    trigger_type=TriggerType.SCHEDULE.value,
                )
                enqueued += 1
                logger.info(
                    "schedule enqueued pipeline=%s cron=%s",
                    pipeline.id, pipeline.schedule_cron,
                )
            except Exception as exc:  # noqa: BLE001 - 锁冲突/配额不应让扫描失败
                logger.warning("schedule skip pipeline=%s reason=%s", pipeline.id, exc)
        logger.info("schedule scan due=%s checked=%s", enqueued, checked)
    return {"enqueued": enqueued, "checked": checked}
