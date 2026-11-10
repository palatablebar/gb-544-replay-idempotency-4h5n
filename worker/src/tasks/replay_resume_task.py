"""中断重放续跑：扫描心跳过期仍停在 queued/running 的批次，重新入队从断点继续。

与 acks_late 的重投互为兜底：消息丢失（broker 重启、任务被 ack 后进程被杀）
时批次不会永远卡住；执行侧的 claim_batch 保证补投不会与在跑执行者重复生效。
"""
from __future__ import annotations

from src.config.database import session_scope
from src.services import replay_service
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app

logger = get_logger("syncmesh.worker.replay_resume")

TASK_REPLAY_RECORDS = "syncmesh.replay_records"


@celery_app.task(name="syncmesh.resume_replays")
def resume_replays() -> dict:
    with session_scope() as db:
        stale = replay_service.stale_active_batches(db)
        resumed = []
        for batch in stale:
            celery_app.send_task(TASK_REPLAY_RECORDS, args=[str(batch.id)])
            resumed.append({"batch_id": str(batch.id), "run_id": str(batch.run_id), "cursor": batch.cursor})
        if resumed:
            logger.warning("replay resume enqueued batches=%s", resumed)
    return {"resumed": len(resumed)}
