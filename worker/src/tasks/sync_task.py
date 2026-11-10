"""单次同步编排：probe → extract → transform → load → verify 全在 worker 里跑。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.config.database import session_scope
from src.constants import error_codes as codes
from src.constants.enums import RunStatus, Stage, SyncMode, TriggerType
from src.models.data_source import DataSource
from src.models.rejected_record import RejectedRecord
from src.models.sync_pipeline import SyncPipeline
from src.models.sync_run import SyncRun
from src.services import mapping_service
from src.utils.errors import AppError
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app
from worker_src.core import lock, progress, storage
from worker_src.core.retry import next_delay, should_retry
from worker_src.pipelines import extract, incremental, load, transform, verify

logger = get_logger("syncmesh.worker.sync")


@celery_app.task(bind=True, name="syncmesh.sync_pipeline", max_retries=0)
def sync_pipeline(self, run_id: str) -> dict:
    with session_scope() as db:
        run = db.get(SyncRun, uuid.UUID(str(run_id)))
        if run is None:
            logger.warning("run not found run=%s", run_id)
            return {"ok": False, "reason": "run_not_found"}
        if run.status == RunStatus.CANCELED.value:
            return {"ok": False, "reason": "canceled"}

        pipeline = db.get(SyncPipeline, run.pipeline_id)
        source = db.get(DataSource, pipeline.source_id) if pipeline else None
        if pipeline is None or source is None:
            progress.finish(
                db, run, status=RunStatus.FAILED.value,
                error_message="管道或数据源已被删除", error_code=codes.NOT_FOUND,
            )
            return {"ok": False, "reason": "pipeline_missing"}

        if not lock.acquire(db, pipeline.id, run.id):
            progress.finish(
                db, run, status=RunStatus.FAILED.value,
                error_message="管道锁冲突：同一条管道已有运行在跑", error_code=codes.PIPELINE_LOCKED,
            )
            return {"ok": False, "reason": "locked"}

        progress.mark_running(db, run)

        try:
            return _run(db, run, pipeline, source)
        except AppError as exc:
            return _handle_failure(db, run, pipeline, exc.code, exc.message, exc.detail)
        except Exception as exc:  # noqa: BLE001
            logger.error("run crashed run=%s error=%s", run.id, exc, exc_info=True)
            return _handle_failure(db, run, pipeline, codes.INTERNAL_ERROR, str(exc), "")
        finally:
            lock.release(db, pipeline.id, run.id)


def _run(db, run: SyncRun, pipeline: SyncPipeline, source: DataSource) -> dict:
    mappings = mapping_service.mapping_dicts(db, pipeline.id)
    if not mappings:
        raise AppError(
            codes.PIPELINE_INVALID_MAPPING, "管道没有字段映射",
            f"SyncPipeline[id={pipeline.id}] run failed: mapping empty",
        )

    incremental_mode = pipeline.sync_mode == SyncMode.INCREMENTAL.value
    watermark_column = pipeline.watermark_column

    # 水位线起点：优先用上次成功推进的值，否则取目标表当前最大值
    target_max = load.target_max_watermark(
        pipeline.target_schema, pipeline.target_table, watermark_column
    )
    wm_from = incremental.watermark_from(pipeline.last_watermark, target_max)
    run.watermark_from = None if wm_from is None else str(wm_from)
    db.commit()

    progress.set_stage(db, run, Stage.EXTRACT.value, watermark_from=run.watermark_from)
    logger.info("extract start run=%s source=%s", run.id, source.source_type)
    source_columns = [mapping["source_field"] for mapping in mappings]
    rows = extract.read_rows(source.source_type, source.config_json or {}, columns=source_columns)

    kept, filtered, next_watermark = incremental.filter_rows(
        rows,
        sync_mode=pipeline.sync_mode,
        watermark_column=watermark_column,
        watermark=wm_from,
    )
    progress.bump_counters(
        db, run,
        rows_read=len(kept),
        watermark_value=None if next_watermark is None else str(next_watermark),
    )
    logger.info(
        "extract done run=%s rows_read=%s filtered=%s", run.id, len(kept), filtered
    )

    if not kept:
        if next_watermark is not None:
            pipeline.last_watermark = str(next_watermark)
        db.commit()
        progress.set_stage(db, run, Stage.VERIFY.value, note="no_new_data")
        progress.finish(db, run, status=RunStatus.SUCCEEDED.value)
        logger.info("run succeeded (no new data) run=%s", run.id)
        return {"ok": True, "rows_read": 0, "no_new_data": True}

    progress.set_stage(db, run, Stage.TRANSFORM.value)
    mapped_records, transform_failures = transform.transform_batch(kept, mappings)
    progress.bump_counters(db, run, rows_rejected=len(transform_failures))

    progress.set_stage(db, run, Stage.LOAD.value)
    staging_table = storage.prepare_staging(pipeline.id)
    storage.write_staging(pipeline.id, staging_table, mapped_records)
    outcome = load.load_to_target(
        schema=pipeline.target_schema,
        table=pipeline.target_table,
        records=mapped_records,
        conflict_strategy=pipeline.conflict_strategy,
        conflict_key=pipeline.conflict_key,
        run_id=run.id,
    )

    rejected_items = list(transform_failures) + list(outcome.rejected)
    for item in rejected_items:
        db.add(
            RejectedRecord(
                run_id=run.id,
                pipeline_id=pipeline.id,
                raw_payload_json=_json_safe(item.get("raw_payload") or {}),
                reason_code=item.get("reason_code") or "transform_failed",
                reason_detail=str(item.get("reason_detail") or "")[:2000],
                source_row_index=int(item.get("source_row_index") or 0),
            )
        )
    db.commit()

    progress.set_stage(db, run, Stage.VERIFY.value)
    staging_rows = storage.count_staging(pipeline.id, staging_table)
    verification = verify.verify_run(
        rows_read=len(kept),
        staging_rows=staging_rows,
        written=outcome.written,
        skipped=outcome.skipped,
        rejected=rejected_items,
    )
    status = verify.final_status(len(rejected_items), None)

    progress.bump_counters(
        db, run,
        rows_written=outcome.written,
        rows_rejected=len(rejected_items),
        rows_skipped=outcome.skipped,
        watermark_value=None if next_watermark is None else str(next_watermark),
    )
    if next_watermark is not None:
        pipeline.last_watermark = str(next_watermark)
    db.commit()

    progress.finish(db, run, status=status)
    if status == RunStatus.PARTIAL.value:
        logger.info(
            "run partial run=%s read=%s written=%s rejected=%s codes=%s",
            run.id, len(kept), outcome.written, len(rejected_items), verification["rejected_codes"],
        )
    else:
        logger.info(
            "run succeeded run=%s read=%s written=%s", run.id, len(kept), outcome.written
        )
    return {
        "ok": True,
        "status": status,
        "rows_read": len(kept),
        "rows_written": outcome.written,
        "rows_rejected": len(rejected_items),
        "verification": verification,
    }


def _handle_failure(db, run: SyncRun, pipeline: SyncPipeline, code: str, message: str, detail: str) -> dict:
    logger.error("run failed run=%s code=%s error=%s detail=%s", run.id, code, message, detail)
    retryable = should_retry(run.retry_count, code)
    if retryable:
        run.retry_count = run.retry_count + 1
        run.status = RunStatus.QUEUED.value
        run.error_code = code
        run.error_message = f"{message}（第 {run.retry_count} 次重试已排期）"
        db.commit()
        delay = next_delay(run.retry_count)
        logger.warning("run retry scheduled run=%s retry=%s delay=%s", run.id, run.retry_count, delay)
        sync_pipeline.apply_async(args=[str(run.id)], countdown=delay)
        return {"ok": False, "retry": run.retry_count, "delay": delay}
    progress.finish(db, run, status=RunStatus.FAILED.value, error_message=f"{message} {detail}".strip(), error_code=code)
    return {"ok": False, "code": code, "error": message}


def _json_safe(payload: dict) -> dict:
    from datetime import date

    safe = {}
    for key, value in payload.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (datetime, date)):
            safe[key] = value.isoformat()
        else:
            safe[key] = str(value)
    return safe
