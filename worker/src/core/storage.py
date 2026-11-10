"""staging schema 落地：每次运行先写入 staging.sync_<pipeline>，再校验写入 target。"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from src.config.database import engine
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("syncmesh.worker.storage")


def staging_table_name(pipeline_id: uuid.UUID) -> str:
    return f"sync_{str(pipeline_id).replace('-', '')[:12]}"


def prepare_staging(pipeline_id: uuid.UUID) -> str:
    table = staging_table_name(pipeline_id)
    schema = settings.staging_schema
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))
        conn.execute(
            text(
                f'CREATE TABLE "{schema}"."{table}" ('
                " row_index integer, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now())"
            )
        )
    logger.info("staging prepared table=%s.%s", schema, table)
    return table


def write_staging(pipeline_id: uuid.UUID, table: str, records: list[dict[str, Any]], start_index: int = 0) -> int:
    import json

    if not records:
        return 0
    schema = settings.staging_schema
    payloads = [
        {"row_index": start_index + offset, "payload": json.dumps(record, ensure_ascii=False, default=str)}
        for offset, record in enumerate(records)
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                f'INSERT INTO "{schema}"."{table}" (row_index, payload) '
                "VALUES (:row_index, CAST(:payload AS jsonb))"
            ),
            payloads,
        )
    return len(payloads)


def count_staging(pipeline_id: uuid.UUID, table: str) -> int:
    schema = settings.staging_schema
    with engine.connect() as conn:
        return int(
            conn.execute(text(f'SELECT count(*) FROM "{schema}"."{table}"')).scalar_one()
        )


def drop_staging(pipeline_id: uuid.UUID) -> None:
    table = staging_table_name(pipeline_id)
    schema = settings.staging_schema
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))


def list_staging_tables() -> list[str]:
    schema = settings.staging_schema
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_name LIKE 'sync_%'"
            ),
            {"schema": schema},
        ).all()
    return [row[0] for row in rows]


def drop_stale_staging(ttl_hours: int) -> list[str]:
    schema = settings.staging_schema
    dropped: list[str] = []
    for table in list_staging_tables():
        try:
            with engine.begin() as conn:
                latest = conn.execute(
                    text(f'SELECT max(created_at) FROM "{schema}"."{table}"')
                ).scalar_one()
                if latest is None:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))
                    dropped.append(table)
                    continue
                too_old = conn.execute(
                    text("SELECT (:latest)::timestamptz < now() - (:ttl)::int * interval '1 hour'"),
                    {"latest": latest, "ttl": ttl_hours},
                ).scalar_one()
                if too_old:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))
                    dropped.append(table)
        except Exception as exc:  # noqa: BLE001
            logger.warning("drop staging failed table=%s error=%s", table, exc)
    return dropped
