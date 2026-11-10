"""重放批次服务：幂等键、get-or-create、重新激活、原子认领、中断扫描。

backend（入队）与 worker（执行）共用这一份，避免两套实现漂移：
- 幂等：batch_key = sha256(run_id + 排序后的 rejected_id 集合)，唯一约束兜底并发；
  活跃批次重复提交直接返回 deduplicated，不再投递。
- 续跑：cursor 是 rejected_ids 的处理位置，每条记录 checkpoint 一次；
  心跳过期的 queued/running 批次由 worker 扫描器重新入队，从 cursor 继续。
- 计数：执行侧对 sync_runs.rows_written 用 SQL 原子自增，rows_rejected 每个
  checkpoint 按 rejected_records 真实行数重算，页面计数始终与库一致。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.constants.enums import ReplayBatchStatus
from src.models.replay_batch import ReplayBatch
from src.models.sync_run import SyncRun
from src.utils.checksum import text_checksum
from src.utils.logger import get_logger

logger = get_logger("syncmesh.replay")

# 心跳多久不刷新视为「进程中断」（worker 每条记录 checkpoint 时都会刷新）
STALE_HEARTBEAT_SECONDS = 60


def batch_key(run_id: Any, record_ids: list[str]) -> str:
    """同一 run 下同一组拒绝行 = 同一批：与处理顺序无关，按 id 字典序排序。"""
    ordered = ",".join(sorted(str(record_id) for record_id in record_ids))
    return text_checksum(f"{run_id}:{ordered}")


def get_or_create_batch(
    db: Session,
    *,
    run: SyncRun,
    record_ids: list[str],
    actor: Any,
    actor_kind: str,
) -> tuple[ReplayBatch, bool]:
    """按幂等键取或建批次。并发下唯一约束只放行一个，其余落回查询。"""
    key = batch_key(run.id, record_ids)
    existing = db.query(ReplayBatch).filter(ReplayBatch.batch_key == key).one_or_none()
    if existing is not None:
        return existing, False
    now = datetime.now(timezone.utc)
    batch = ReplayBatch(
        run_id=run.id,
        pipeline_id=run.pipeline_id,
        batch_key=key,
        status=ReplayBatchStatus.QUEUED.value,
        total=len(record_ids),
        cursor=0,
        rejected_ids=[str(record_id) for record_id in record_ids],
        actor_id=getattr(actor, "id", None),
        actor_kind=actor_kind,
        heartbeat_at=now,
        created_at=now,
    )
    db.add(batch)
    try:
        db.commit()
    except IntegrityError:
        # 并发同事务插入同一 batch_key：回滚后取先到的那个
        db.rollback()
        existing = db.query(ReplayBatch).filter(ReplayBatch.batch_key == key).one()
        return existing, False
    db.refresh(batch)
    return batch, True


def reactivate_batch(db: Session, batch: ReplayBatch) -> None:
    """终态批次被再次提交：归零重跑。

    已成功写入的拒绝行早已从 rejected_records 删除，重跑时自然跳过；
    仍拒绝的行会被重试。真正的「断点续跑」发生在活跃批次上：进程中断后
    心跳过期，由续跑扫描器重新入队，cursor 原样保留。
    """
    batch.cursor = 0
    batch.written = 0
    batch.still_rejected = 0
    batch.status = ReplayBatchStatus.QUEUED.value
    batch.error_message = None
    batch.claim_token = None
    batch.finished_at = None
    batch.heartbeat_at = datetime.now(timezone.utc)
    db.commit()


def mark_enqueue_failed(db: Session, batch: ReplayBatch, detail: str) -> None:
    batch.status = ReplayBatchStatus.FAILED.value
    batch.error_message = f"无法投递到 worker：{detail}"[:2000]
    batch.finished_at = datetime.now(timezone.utc)
    db.commit()


def claim_batch(db: Session, batch_id: Any, token: str) -> ReplayBatch | None:
    """执行层原子认领：只有 queued / 心跳过期的 running / 同一令牌重投 才能认领。

    认领先到先得，抢不到的重复投递直接返回 None，保证同一批只生效一次。
    """
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=STALE_HEARTBEAT_SECONDS)
    result = db.execute(
        update(ReplayBatch)
        .where(ReplayBatch.id == batch_id)
        .where(
            or_(
                ReplayBatch.status == ReplayBatchStatus.QUEUED.value,
                and_(
                    ReplayBatch.status == ReplayBatchStatus.RUNNING.value,
                    ReplayBatch.heartbeat_at < stale_before,
                ),
                ReplayBatch.claim_token == token,
            )
        )
        .values(
            status=ReplayBatchStatus.RUNNING.value,
            claim_token=token,
            heartbeat_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if result.rowcount == 0:
        return None
    batch = db.get(ReplayBatch, batch_id)
    db.refresh(batch)
    return batch


def bump_rows_written(db: Session, run_id: Any, written: int) -> None:
    """SQL 级原子自增：并发批次互不覆盖，不用读-改-写。"""
    if written <= 0:
        return
    db.execute(
        update(SyncRun)
        .where(SyncRun.id == run_id)
        .values(rows_written=SyncRun.rows_written + written)
        .execution_options(synchronize_session=False)
    )


def checkpoint(
    db: Session,
    batch: ReplayBatch,
    *,
    token: str,
    cursor: int,
    run: SyncRun,
    remaining_rejected: int,
) -> bool:
    """每条记录处理完提交一次：游标 + 心跳 + 运行剩余拒绝数（与库实时一致）。

    游标更新带 claim_token 栅栏：丢权的僵尸执行者提交失败返回 False，
    调用方应立即中止，本事务内的计数修改一并回滚。
    """
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(ReplayBatch)
        .where(ReplayBatch.id == batch.id, ReplayBatch.claim_token == token)
        .values(cursor=cursor, heartbeat_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        db.rollback()
        return False
    run.rows_rejected = remaining_rejected
    db.commit()
    batch.cursor = cursor
    batch.heartbeat_at = now
    return True


def finish_batch(
    db: Session,
    batch: ReplayBatch,
    *,
    token: str,
    run: SyncRun,
    remaining_rejected: int,
) -> bool:
    from src.constants.enums import RunStatus

    final_status = (
        ReplayBatchStatus.SUCCEEDED.value
        if batch.still_rejected == 0
        else ReplayBatchStatus.PARTIAL.value
    )
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(ReplayBatch)
        .where(ReplayBatch.id == batch.id, ReplayBatch.claim_token == token)
        .values(status=final_status, finished_at=now, heartbeat_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        db.rollback()
        return False
    run.rows_rejected = remaining_rejected
    if run.status == RunStatus.PARTIAL.value and remaining_rejected == 0:
        run.status = RunStatus.SUCCEEDED.value
    db.commit()
    batch.status = final_status
    batch.finished_at = now
    return True


def fail_batch(db: Session, batch: ReplayBatch, *, token: str, detail: str) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(ReplayBatch)
        .where(ReplayBatch.id == batch.id, ReplayBatch.claim_token == token)
        .values(
            status=ReplayBatchStatus.FAILED.value,
            error_message=detail[:2000],
            finished_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    batch.status = ReplayBatchStatus.FAILED.value


def stale_active_batches(db: Session) -> list[ReplayBatch]:
    """心跳过期仍停在 queued/running 的批次：进程中断，需要重新入队续跑。"""
    stale_before = datetime.now(timezone.utc) - timedelta(seconds=STALE_HEARTBEAT_SECONDS)
    return (
        db.query(ReplayBatch)
        .filter(
            ReplayBatch.status.in_(ReplayBatchStatus.active()),
            ReplayBatch.heartbeat_at < stale_before,
        )
        .order_by(ReplayBatch.created_at.asc())
        .all()
    )


def latest_batches(db: Session, run_id: Any, limit: int = 5) -> list[ReplayBatch]:
    return (
        db.query(ReplayBatch)
        .filter(ReplayBatch.run_id == run_id)
        .order_by(ReplayBatch.created_at.desc())
        .limit(limit)
        .all()
    )
