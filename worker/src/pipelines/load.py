"""写入：staging 落地 → 目标表按冲突策略 upsert。"""
from __future__ import annotations

import uuid
from typing import Any

from src.config.database import session_scope
from src.services import load_service
from src.utils.logger import get_logger
from worker_src.core import storage

logger = get_logger("syncmesh.worker.load")


def write_staging(pipeline_id: uuid.UUID, table: str, records: list[dict[str, Any]]) -> int:
    clean = [{k: v for k, v in record.items() if not k.startswith("__")} for record in records]
    return storage.write_staging(pipeline_id, table, clean)


def load_to_target(
    *,
    schema: str,
    table: str,
    records: list[dict[str, Any]],
    conflict_strategy: str,
    conflict_key: str | None,
    run_id: uuid.UUID,
) -> load_service.LoadOutcome:
    outcome = load_service.insert_rows(
        schema, table, records, conflict_strategy, conflict_key, run_id
    )
    logger.info(
        "load done written=%s skipped=%s rejected=%s",
        outcome.written,
        outcome.skipped,
        outcome.rejected_count,
    )
    return outcome


def target_max_watermark(schema: str, table: str, column: str | None) -> Any:
    if not column:
        return None
    from sqlalchemy import text

    from src.config.database import engine

    try:
        with engine.connect() as conn:
            return conn.execute(
                text(f'SELECT max("{column}") FROM "{schema}"."{table}"')
            ).scalar_one()
    except Exception:  # noqa: BLE001
        return None
