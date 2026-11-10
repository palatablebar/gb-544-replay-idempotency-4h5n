"""初始化三个 schema：meta 平台表、target 目标表、staging 中间表。

Revision ID: 0001_initial
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from src.config.settings import settings
from src.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

META = settings.meta_schema
STAGING = settings.staging_schema
TARGET = settings.target_schema

TARGET_DDL = f"""
CREATE TABLE IF NOT EXISTS {TARGET}.store_sales (
    store_no        text          NOT NULL,
    sale_date       date          NOT NULL,
    sku             text          NOT NULL,
    qty             integer       NOT NULL DEFAULT 0,
    amount          numeric(12,2) NOT NULL DEFAULT 0,
    updated_at      timestamp     NOT NULL,
    _sync_run_id    uuid,
    _synced_at      timestamptz,
    PRIMARY KEY (store_no, sku)
);

CREATE TABLE IF NOT EXISTS {TARGET}.members (
    member_id       text          PRIMARY KEY,
    mobile          text,
    tier            text,
    updated_at      timestamp     NOT NULL,
    _sync_run_id    uuid,
    _synced_at      timestamptz
);

CREATE TABLE IF NOT EXISTS {TARGET}.channel_orders (
    order_id        bigint        PRIMARY KEY,
    member_id       text,
    amount          numeric(12,2),
    channel         text,
    order_status    text,
    updated_at      timestamp,
    _sync_run_id    uuid,
    _synced_at      timestamptz
);

CREATE TABLE IF NOT EXISTS {TARGET}.members_source (
    member_id       text          PRIMARY KEY,
    mobile          text,
    tier            text,
    updated_at      timestamp     NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_store_sales_run ON {TARGET}.store_sales (_sync_run_id);
CREATE INDEX IF NOT EXISTS idx_members_run ON {TARGET}.members (_sync_run_id);
CREATE INDEX IF NOT EXISTS idx_channel_orders_run ON {TARGET}.channel_orders (_sync_run_id);
CREATE INDEX IF NOT EXISTS idx_members_source_updated ON {TARGET}.members_source (updated_at);
"""


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {META}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {STAGING}")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {TARGET}")

    # meta 平台表：模型定义即真相
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

    # target 业务表（含 _sync_run_id / _synced_at 两个审计列）
    for statement in [part.strip() for part in TARGET_DDL.split(";") if part.strip()]:
        op.execute(sa.text(statement))


def downgrade() -> None:
    op.execute(f"DROP SCHEMA IF EXISTS {STAGING} CASCADE")
    op.execute(f"DROP SCHEMA IF EXISTS {TARGET} CASCADE")
    op.execute(f"DROP SCHEMA IF EXISTS {META} CASCADE")
