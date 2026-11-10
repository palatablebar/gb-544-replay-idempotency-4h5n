"""运行服务：入队（配额 + 锁 + 审计）、列表、详情、取消、重放投递。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.config.celery_app import TASK_REPLAY_RECORDS, TASK_SYNC_PIPELINE, celery_app
from src.constants import error_codes as codes
from src.constants.enums import RunStatus, TriggerType
from src.models.data_source import DataSource
from src.models.pipeline_lock import PipelineLock
from src.models.rejected_record import RejectedRecord
from src.models.sync_pipeline import SyncPipeline
from src.models.sync_run import SyncRun
from src.schemas.rejected import serialize_rejected
from src.schemas.run import serialize_run
from src.services import mapping_service, quota_service
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger

logger = get_logger("syncmesh.run")


def get_run(db: Session, run_id: Any) -> SyncRun:
    run = db.get(SyncRun, run_id)
    if run is None:
        raise not_found("SyncRun", run_id)
    return run


def _pipeline_map(db: Session) -> dict[Any, SyncPipeline]:
    return {pipeline.id: pipeline for pipeline in db.query(SyncPipeline).all()}


def _lock_conflict(db: Session, pipeline_id: Any) -> PipelineLock | None:
    now = datetime.now(timezone.utc)
    return (
        db.query(PipelineLock)
        .filter(PipelineLock.pipeline_id == pipeline_id, PipelineLock.locked_until > now)
        .one_or_none()
    )


def create_run(
    db: Session,
    *,
    pipeline: SyncPipeline,
    user: Any,
    trigger_type: str = TriggerType.MANUAL.value,
    actor_kind: str = "user",
) -> SyncRun:
    if trigger_type != TriggerType.SCHEDULE.value:
        quota_service.check_quota(db, user)
    lock = _lock_conflict(db, pipeline.id)
    if lock is not None:
        raise AppError(
            codes.PIPELINE_LOCKED,
            "这条管道正在跑，去看当前运行",
            f"pipeline={pipeline.id} locked_until={lock.locked_until.isoformat()}",
            extra={"locked_run_id": str(lock.run_id) if lock.run_id else None},
        )
    active_for_pipeline = (
        db.query(SyncRun)
        .filter(
            SyncRun.pipeline_id == pipeline.id,
            SyncRun.status.in_((RunStatus.QUEUED.value, RunStatus.RUNNING.value)),
        )
        .first()
    )
    if active_for_pipeline is not None:
        raise AppError(
            codes.PIPELINE_LOCKED,
            "这条管道正在跑，去看当前运行",
            f"pipeline={pipeline.id} active_run={active_for_pipeline.id}",
            extra={"locked_run_id": str(active_for_pipeline.id)},
        )

    run = SyncRun(
        pipeline_id=pipeline.id,
        trigger_type=trigger_type,
        triggered_by=getattr(user, "id", None),
        actor_kind=actor_kind,
        status=RunStatus.QUEUED.value,
        stage="probe",
        stage_history=[],
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        celery_app.send_task(TASK_SYNC_PIPELINE, args=[str(run.id)])
    except Exception as exc:  # noqa: BLE001 - broker 不可用时如实标记失败
        logger.error("run enqueue failed run=%s error=%s", run.id, exc)
        run.status = RunStatus.FAILED.value
        run.error_code = codes.INTERNAL_ERROR
        run.error_message = f"无法投递到 worker：{exc}"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise AppError(
            codes.INTERNAL_ERROR, "无法投递运行任务到 worker", str(exc)
        ) from exc
    logger.info("run enqueued run=%s pipeline=%s", run.id, pipeline.id)
    return run


def list_runs(
    db: Session, *, status: str | None = None, pipeline_id: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    query = db.query(SyncRun)
    if status:
        query = query.filter(SyncRun.status == status)
    if pipeline_id:
        query = query.filter(SyncRun.pipeline_id == pipeline_id)
    runs = query.order_by(SyncRun.created_at.desc()).limit(limit).all()
    pipelines = _pipeline_map(db)
    sources = {source.id: source for source in db.query(DataSource).all()}
    payload = []
    for run in runs:
        pipeline = pipelines.get(run.pipeline_id)
        source = sources.get(pipeline.source_id) if pipeline else None
        payload.append(
            serialize_run(
                run,
                pipeline_name=pipeline.name if pipeline else None,
                source_type=source.source_type if source else None,
            )
        )
    return payload


def run_detail(db: Session, run_id: Any) -> dict[str, Any]:
    from src.services import extract_service

    run = get_run(db, run_id)
    pipeline = db.get(SyncPipeline, run.pipeline_id)
    source = db.get(DataSource, pipeline.source_id) if pipeline else None
    rejected = (
        db.query(RejectedRecord)
        .filter(RejectedRecord.run_id == run.id)
        .order_by(RejectedRecord.created_at.asc())
        .all()
    )
    payload = serialize_run(
        run,
        pipeline_name=pipeline.name if pipeline else None,
        source_type=source.source_type if source else None,
    )
    payload["pipeline"] = {
        "id": str(pipeline.id),
        "name": pipeline.name,
        "target_full_name": f"{pipeline.target_schema}.{pipeline.target_table}",
        "sync_mode": pipeline.sync_mode,
        "watermark_column": pipeline.watermark_column,
        "conflict_strategy": pipeline.conflict_strategy,
        "conflict_key": pipeline.conflict_key,
    } if pipeline else None
    payload["mappings"] = mapping_service.mapping_dicts(db, run.pipeline_id)
    payload["rejected"] = [serialize_rejected(record) for record in rejected]
    payload["rejected_by_reason"] = _group_reasons(rejected)
    payload["diff"] = _build_diff(db, run, pipeline, source, extract_service)
    return payload


def _group_reasons(rejected: list[RejectedRecord]) -> dict[str, int]:
    grouped: dict[str, int] = {}
    for record in rejected:
        grouped[record.reason_code] = grouped.get(record.reason_code, 0) + 1
    return grouped


def _build_diff(
    db: Session,
    run: SyncRun,
    pipeline: SyncPipeline | None,
    source: DataSource | None,
    extract_service: Any,
    limit: int = 8,
) -> dict[str, Any]:
    """源样本 vs 落库样本：按冲突键把本批源行与本次运行写入的目标行配对。"""
    from src.services import load_service, transform_service

    if pipeline is None:
        return {"source_rows": [], "target_rows": [], "target_columns": []}
    mappings = mapping_service.mapping_dicts(db, run.pipeline_id)
    source_columns = [mapping["source_field"] for mapping in mappings]
    key_columns = [part.strip() for part in (pipeline.conflict_key or "").split(",") if part.strip()]

    try:
        rows = extract_service.read_source_rows(
            source.source_type if source else "csv",
            source.config_json if source else {},
            columns=source_columns,
        )
    except Exception:  # noqa: BLE001 - 详情页不能因源不可达而 500
        rows = []

    try:
        page = load_service.browse_target(
            pipeline.target_schema, pipeline.target_table, page=1, page_size=200
        )
        run_rows = [
            row for row in page["rows"] if str(row.get("_sync_run_id") or "") == str(run.id)
        ]
        if not run_rows:
            run_rows = page["rows"]
    except Exception:  # noqa: BLE001
        run_rows = []

    target_index: dict[tuple, dict[str, Any]] = {}
    if key_columns:
        for row in run_rows:
            target_index[tuple(str(row.get(column)) for column in key_columns)] = row

    paired_source: list[dict[str, Any]] = []
    paired_target: list[dict[str, Any]] = []
    for row in rows[: max(limit, 20)]:
        mapped, _failures = transform_service.transform_row(row, mappings)
        key = tuple(str(mapped.get(column)) for column in key_columns) if key_columns else ()
        candidate = target_index.get(key)
        if candidate is None and not key_columns and run_rows:
            candidate = run_rows[len(paired_source)] if len(paired_source) < len(run_rows) else None
        if candidate is None:
            continue
        paired_source.append(row)
        paired_target.append(candidate)
        if len(paired_source) >= limit:
            break

    return {
        "source_rows": paired_source or rows[:limit],
        "target_rows": paired_target or run_rows[:limit],
        "target_columns": mappings,
    }


def cancel_run(db: Session, run_id: Any) -> SyncRun:
    run = get_run(db, run_id)
    if run.status in RunStatus.terminal():
        raise AppError(
            codes.PIPELINE_INACTIVE, "该运行已结束，无法取消", f"status={run.status}"
        )
    run.status = RunStatus.CANCELED.value
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    return run


def replay_records(
    db: Session,
    *,
    run: SyncRun,
    rejected_ids: list[str],
    reason_code: str | None,
    actor: Any,
    actor_kind: str = "user",
) -> dict[str, Any]:
    query = db.query(RejectedRecord).filter(RejectedRecord.run_id == run.id)
    if rejected_ids:
        query = query.filter(RejectedRecord.id.in_(rejected_ids))
    if reason_code:
        query = query.filter(RejectedRecord.reason_code == reason_code)
    records = query.order_by(RejectedRecord.created_at.asc()).all()
    if not records:
        raise AppError(codes.REPLAY_EMPTY, "没有可重放的记录", f"run={run.id}")
    try:
        celery_app.send_task(
            TASK_REPLAY_RECORDS,
            args=[str(run.id), [str(record.id) for record in records]],
            kwargs={"actor_id": str(getattr(actor, "id", "")), "actor_kind": actor_kind},
        )
    except Exception as exc:  # noqa: BLE001
        raise AppError(codes.INTERNAL_ERROR, "无法投递重放任务", str(exc)) from exc
    return {"queued": len(records), "run_id": str(run.id)}


def resolve_actor(db: Session, user_id: Any):
    from src.models.user import User

    return db.get(User, user_id) if user_id else None
