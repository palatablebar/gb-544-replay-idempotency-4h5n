"""重放批次表：幂等键 + 游标断点 + 执行认领，支撑重放只生效一次与中断续跑。

Revision ID: 0002_replay_batches
"""
from __future__ import annotations

from alembic import op

from src.models.replay_batch import ReplayBatch

revision = "0002_replay_batches"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 模型定义即真相；checkfirst 兼容「0001 已用 create_all 建过」的全新库
    ReplayBatch.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    ReplayBatch.__table__.drop(bind=op.get_bind(), checkfirst=True)
