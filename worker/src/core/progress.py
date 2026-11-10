"""阶段与行数回写：sync_task 每个阶段调用一次，保证前端轮询能看到推进。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.constants.enums import RunStatus, Stage
from src.models.sync_run import SyncRun
from src.utils.logger import get_logger
from worker_src.constants.stages import STAGE_LABELS, STAGE_ORDER

logger = get_logger("syncmesh.worker.progress")


def mark_running(db: Session, run: SyncRun) -> None:
    run.status = RunStatus.RUNNING.value
    run.started_at = run.started_at or datetime.now(timezone.utc)
    run.stage = Stage.PROBE.value
    run.stage_history = [{"stage": Stage.PROBE.value, "at": datetime.now(timezone.utc).isoformat()}]
    db.commit()


def set_stage(db: Session, run: SyncRun, stage: str, **extra: Any) -> None:
    history = list(run.stage_history or [])
    history.append(
        {
            "stage": stage,
            "label": STAGE_LABELS.get(stage, stage),
            "at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
    )
    run.stage = stage
    run.stage_history = history
    db.commit()
    logger.info("run=%s stage=%s", run.id, stage)


def bump_counters(
    db: Session,
    run: SyncRun,
    *,
    rows_read: int | None = None,
    rows_written: int | None = None,
    rows_rejected: int | None = None,
    rows_skipped: int | None = None,
    watermark_value: str | None = None,
) -> None:
    if rows_read is not None:
        run.rows_read = rows_read
    if rows_written is not None:
        run.rows_written = rows_written
    if rows_rejected is not None:
        run.rows_rejected = rows_rejected
    if rows_skipped is not None:
        run.rows_skipped = rows_skipped
    if watermark_value is not None:
        run.watermark_value = watermark_value
    db.commit()


def finish(
    db: Session,
    run: SyncRun,
    *,
    status: str,
    error_message: str | None = None,
    error_code: str | None = None,
) -> None:
    run.status = status
    run.error_message = error_message
    run.error_code = error_code
    run.finished_at = datetime.now(timezone.utc)
    db.commit()


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 0


def write_artifact(run_id: uuid.UUID, name: str, payload: str) -> str:
    """把拒绝行/运行报告写到 artifact 卷，返回相对路径。"""
    import os

    base = os.environ.get("ARTIFACT_DIR", "/data/artifacts")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{run_id}-{name}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return path
