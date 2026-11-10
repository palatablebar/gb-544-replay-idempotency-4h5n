"""调度服务：cron 解析与到期判定（croniter），worker 的 schedule_task 复用。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from croniter import croniter
from sqlalchemy.orm import Session

from src.constants.enums import PipelineStatus
from src.models.sync_pipeline import SyncPipeline
from src.models.sync_run import SyncRun


def validate_cron(expr: str) -> bool:
    return bool(croniter.is_valid(expr))


def next_due_after(cron_expr: str, base: datetime) -> datetime | None:
    if not validate_cron(cron_expr):
        return None
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return croniter(cron_expr, base).get_next(datetime)


def is_due(pipeline: SyncPipeline, now: datetime) -> bool:
    if pipeline.status != PipelineStatus.ACTIVE.value or not pipeline.schedule_cron:
        return False
    if not validate_cron(pipeline.schedule_cron):
        return False
    return True


def last_run_at(db: Session, pipeline_id: Any) -> datetime | None:
    run = (
        db.query(SyncRun)
        .filter(SyncRun.pipeline_id == pipeline_id)
        .order_by(SyncRun.created_at.desc())
        .first()
    )
    return run.created_at if run else None


def scan_due_pipelines(db: Session, now: datetime | None = None) -> list[SyncPipeline]:
    """返回此刻应当触发的管道：上次运行时间之后的下一个 cron 时刻已到。"""
    now = now or datetime.now(timezone.utc)
    due: list[SyncPipeline] = []
    pipelines = (
        db.query(SyncPipeline)
        .filter(SyncPipeline.status == PipelineStatus.ACTIVE.value)
        .all()
    )
    for pipeline in pipelines:
        if not pipeline.schedule_cron or not validate_cron(pipeline.schedule_cron):
            continue
        baseline = last_run_at(db, pipeline.id) or pipeline.created_at
        if baseline.tzinfo is None:
            baseline = baseline.replace(tzinfo=timezone.utc)
        next_time = croniter(pipeline.schedule_cron, baseline).get_next(datetime)
        if next_time <= now:
            due.append(pipeline)
    return due


def describe(cron_expr: str | None) -> str:
    from src.utils.formatters import cron_text

    return cron_text(cron_expr)
