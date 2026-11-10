"""拒绝行重放：用当前映射重算原始载荷，再按同一冲突策略写回目标表。"""
from __future__ import annotations

import uuid

from src.config.database import session_scope
from src.constants.enums import RunStatus
from src.models.rejected_record import RejectedRecord
from src.models.sync_pipeline import SyncPipeline
from src.models.sync_run import SyncRun
from src.services import mapping_service
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app
from worker_src.pipelines import load, transform

logger = get_logger("syncmesh.worker.replay")


@celery_app.task(name="syncmesh.replay_records")
def replay_records(run_id: str, rejected_ids: list[str], actor_id: str = "", actor_kind: str = "user") -> dict:
    replayed = 0
    written = 0
    still_rejected = 0
    with session_scope() as db:
        run = db.get(SyncRun, uuid.UUID(str(run_id)))
        if run is None:
            return {"ok": False, "reason": "run_not_found"}
        pipeline = db.get(SyncPipeline, run.pipeline_id)
        if pipeline is None:
            return {"ok": False, "reason": "pipeline_not_found"}
        mappings = mapping_service.mapping_dicts(db, pipeline.id)
        logger.info(
            "replay start run=%s records=%s actor=%s:%s",
            run.id, len(rejected_ids), actor_kind, actor_id,
        )
        for rejected_id in rejected_ids:
            record = db.get(RejectedRecord, uuid.UUID(str(rejected_id)))
            if record is None or str(record.run_id) != str(run.id):
                continue
            replayed += 1
            mapped, failures = transform.transform_one(record.raw_payload_json or {}, mappings)
            if failures or mapped is None:
                still_rejected += 1
                record.reason_detail = (failures[0]["reason_detail"] if failures else record.reason_detail)[:2000]
                db.commit()
                continue
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
                run.rows_written = (run.rows_written or 0) + outcome.written
                run.rows_rejected = max((run.rows_rejected or 0) - 1, 0)
                written += outcome.written
                db.commit()
            else:
                still_rejected += 1
                db.commit()

        reloaded = (
            db.query(RejectedRecord).filter(RejectedRecord.run_id == run.id).count()
        )
        run.rows_rejected = reloaded
        if run.status == RunStatus.PARTIAL.value and reloaded == 0:
            run.status = RunStatus.SUCCEEDED.value
        db.commit()
        logger.info(
            "replay done run=%s replayed=%s written=%s still_rejected=%s",
            run.id, replayed, written, still_rejected,
        )
    return {
        "ok": True,
        "replayed": replayed,
        "written": written,
        "still_rejected": still_rejected,
    }
