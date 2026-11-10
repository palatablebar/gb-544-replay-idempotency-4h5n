"""重放批次：同一批拒绝行的投递只生效一次（batch_key 唯一），游标断点续跑。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.settings import settings
from src.models.base import Base, new_uuid, utcnow


class ReplayBatch(Base):
    __tablename__ = "replay_batches"
    __table_args__ = {"schema": settings.meta_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.meta_schema}.sync_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # 幂等键：sha256(run_id + 排序后的 rejected_id 集合)，同一批重复投递命中唯一约束
    batch_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 已处理位置（rejected_ids 的下标）：每条记录提交一次，中断后从这里续跑
    cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    still_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    # 执行层认领令牌（celery task id）：重复投递时第二个执行者认领不到行即退出
    claim_token: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 游标心跳：每次 checkpoint 刷新；过期即视为进程中断，由续跑扫描器重新入队
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
