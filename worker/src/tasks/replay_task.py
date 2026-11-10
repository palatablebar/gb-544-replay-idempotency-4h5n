"""拒绝行重放：认领批次 → 从游标断点续跑 → 每条记录 checkpoint。

幂等三道防线：
1. 提交侧 batch_key 唯一（run_service.get_or_create_batch），同一批不重复入队；
2. 执行侧 claim_batch 原子认领，broker 重投 / 扫描器补投的重复消息抢不到即退出；
3. 记录侧已成功行已从 rejected_records 删除，续跑自然跳过；游标更新带
   claim_token 栅栏，丢权的僵尸执行者提交失败立即中止。

计数一致性：rows_written 用 SQL 原子自增；rows_rejected 每个 checkpoint 按
rejected_records 真实行数重算，页面轮询看到的永远与库一致。
"""
from __future__ import annotations

import uuid

from src.config.database import session_scope
from src.constants.enums import ReplayBatchStatus
from src.models.rejected_record import RejectedRecord
from src.models.replay_batch import ReplayBatch
from src.models.sync_pipeline import SyncPipeline
from src.models.sync_run import SyncRun
from src.services import mapping_service, replay_service
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app
from worker_src.pipelines import load, transform

logger = get_logger("syncmesh.worker.replay")


@celery_app.task(bind=True, name="syncmesh.replay_records", acks_late=True, max_retries=0)
def replay_records(self, batch_id: str) -> dict:
    token = str(self.request.id or uuid.uuid4())
    with session_scope() as db:
        batch = db.get(ReplayBatch, uuid.UUID(str(batch_id)))
        if batch is None:
            return {"ok": False, "reason": "batch_not_found"}
        if batch.status in ReplayBatchStatus.terminal():
            return {"ok": True, "reason": "already_done", "status": batch.status}

        batch = replay_service.claim_batch(db, batch.id, token)
        if batch is None:
            logger.info("replay claim lost batch=%s token=%s", batch_id, token)
            return {"ok": False, "reason": "claimed_by_other"}

        run = db.get(SyncRun, batch.run_id)
        pipeline = db.get(SyncPipeline, run.pipeline_id) if run else None
        if run is None or pipeline is None:
            replay_service.fail_batch(db, batch, token=token, detail="运行或管道已被删除")
            return {"ok": False, "reason": "run_or_pipeline_missing"}
        mappings = mapping_service.mapping_dicts(db, pipeline.id)
        record_ids = [str(record_id) for record_id in (batch.rejected_ids or [])]
        logger.info(
            "replay start batch=%s run=%s total=%s resumed_from=%s actor=%s:%s",
            batch.id, run.id, len(record_ids), batch.cursor, batch.actor_kind, batch.actor_id,
        )

        try:
            for index in range(batch.cursor, len(record_ids)):
                record = db.get(RejectedRecord, uuid.UUID(record_ids[index]))
                if record is not None and str(record.run_id) == str(run.id):
                    _process_one(db, batch, record, run, pipeline, mappings)
                remaining = db.query(RejectedRecord).filter(RejectedRecord.run_id == run.id).count()
                if not replay_service.checkpoint(
                    db, batch, token=token, cursor=index + 1, run=run,
                    remaining_rejected=remaining,
                ):
                    logger.warning("replay lost claim mid-run batch=%s cursor=%s", batch.id, index)
                    return {"ok": False, "reason": "claim_lost", "cursor": index}
        except Exception as exc:  # noqa: BLE001 - 失败落库，重新提交同批即可从断点续跑
            db.rollback()
            logger.error("replay crashed batch=%s error=%s", batch.id, exc, exc_info=True)
            replay_service.fail_batch(db, batch, token=token, detail=str(exc))
            return {"ok": False, "reason": "crashed", "error": str(exc)}

        remaining = db.query(RejectedRecord).filter(RejectedRecord.run_id == run.id).count()
        if not replay_service.finish_batch(
            db, batch, token=token, run=run, remaining_rejected=remaining
        ):
            return {"ok": False, "reason": "claim_lost", "cursor": batch.cursor}
        logger.info(
            "replay done batch=%s run=%s written=%s still_rejected=%s remaining=%s",
            batch.id, run.id, batch.written, batch.still_rejected, remaining,
        )
        return {
            "ok": True,
            "batch_id": str(batch.id),
            "processed": batch.cursor,
            "written": batch.written,
            "still_rejected": batch.still_rejected,
        }


def _process_one(db, batch, record, run, pipeline, mappings) -> None:
    """单条重放：转换 → 按管道冲突策略写回 → 成功即删拒绝行并原子计数。"""
    mapped, failures = transform.transform_one(record.raw_payload_json or {}, mappings)
    if failures or mapped is None:
        batch.still_rejected += 1
        record.reason_detail = (failures[0]["reason_detail"] if failures else record.reason_detail)[:2000]
        return
    outcome = load.load_to_target(
        schema=pipeline.target_schema,
        table=pipeline.target_table,
        records=[mapped],
        conflict_strategy=pipeline.conflict_strategy,
        conflict_key=pipeline.conflict_key,
        run_id=run.id,
    )
    if outcome.written > 0 and not outcome.rejected:
        db.delete(record)
        db.flush()  # 让同事务的剩余拒绝数统计看到这次删除
        replay_service.bump_rows_written(db, run.id, outcome.written)
        batch.written += outcome.written
    else:
        batch.still_rejected += 1
