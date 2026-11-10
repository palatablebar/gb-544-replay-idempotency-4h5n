"""写入服务：目标表反射、三种冲突策略真实生效、staging → target 落地。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import ConflictStrategy
from src.utils.errors import AppError

AUDIT_COLUMNS = ("_sync_run_id", "_synced_at")

_reflect_engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5)
_reflect_cache: dict[tuple[str, str], Table] = {}


def reflect_table(schema: str, table: str) -> Table:
    key = (schema, table)
    if key in _reflect_cache:
        return _reflect_cache[key]
    inspector = inspect(_reflect_engine)
    if not inspector.has_table(table, schema=schema):
        raise AppError(
            codes.TARGET_TABLE_MISSING, "目标表不存在", f"target_table={schema}.{table} not found"
        )
    metadata = MetaData(schema=schema)
    reflected = Table(table, metadata, schema=schema, autoload_with=_reflect_engine)
    _reflect_cache[key] = reflected
    return reflected


def table_columns(schema: str, table: str) -> list[dict[str, Any]]:
    inspector = inspect(_reflect_engine)
    if not inspector.has_table(table, schema=schema):
        raise AppError(codes.TARGET_TABLE_MISSING, "目标表不存在", f"{schema}.{table} not found")
    columns = []
    for col in inspector.get_columns(table, schema=schema):
        columns.append(
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": bool(col.get("nullable", True)),
                "is_audit": col["name"] in AUDIT_COLUMNS,
            }
        )
    return columns


def parse_conflict_key(conflict_key: str | None) -> list[str]:
    if not conflict_key:
        raise AppError(codes.CONFLICT_KEY_ABSENT, "冲突策略生效但未配置冲突键", "conflict_key empty")
    keys = [part.strip() for part in conflict_key.split(",") if part.strip()]
    if not keys:
        raise AppError(codes.CONFLICT_KEY_ABSENT, "冲突策略生效但未配置冲突键", "conflict_key empty")
    return keys


def _dedupe(
    records: list[dict[str, Any]],
    key_columns: list[str],
    strategy: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """同批次内重复键处理：overwrite 保留最后一条；skip / reject 保留第一条并产出冲突。"""
    if not key_columns:
        return records, []
    seen: dict[tuple, int] = {}
    kept: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    replace_on_dup = strategy == ConflictStrategy.OVERWRITE.value
    for record in records:
        key = tuple(str(record.get(column)) for column in key_columns)
        if key in seen:
            if replace_on_dup:
                kept[seen[key]] = record
            else:
                conflicts.append(
                    {
                        "reason_code": "conflict_rejected",
                        "reason_detail": (
                            f"batch_duplicate conflict_key={'+'.join(key_columns)} value={key}"
                        ),
                        "raw_payload": record.get("__raw_payload__", record),
                        "source_row_index": record.get("__source_row_index__", 0),
                    }
                )
            continue
        seen[key] = len(kept)
        kept.append(record)
    return kept, conflicts


def _existing_keys(
    table: Table,
    key_columns: list[str],
    records: list[dict[str, Any]],
) -> set[tuple]:
    """把冲突键列 cast 成 text 再比较：目标列可能是 bigint/date，来源是 str。"""
    if not key_columns or not records:
        return set()
    from sqlalchemy import String, cast, tuple_

    text_columns = [cast(table.c[name], String) for name in key_columns]
    tuples = {
        tuple(str(record.get(column)) for column in key_columns) for record in records
    }
    ordered = list(tuples)
    found: set[tuple] = set()
    with _reflect_engine.connect() as conn:
        for chunk_start in range(0, len(ordered), 500):
            chunk = ordered[chunk_start : chunk_start + 500]
            stmt = select(*text_columns)
            if len(key_columns) == 1:
                stmt = stmt.where(text_columns[0].in_([chunk_value[0] for chunk_value in chunk]))
            else:
                stmt = stmt.where(tuple_(*text_columns).in_(chunk))
            for row in conn.execute(stmt).all():
                found.add(tuple(str(value) for value in row))
    return found


def coerce_value(column_type: Any, value: Any) -> Any:
    """按目标列类型做最小必要的强制转换（来源行基本都是字符串）。"""
    from sqlalchemy import BigInteger, Boolean, Float, Integer, Numeric, SmallInteger

    if value is None or value == "":
        return None
    if isinstance(column_type, (Integer, SmallInteger, BigInteger)):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).replace(",", "").strip()
        try:
            return int(float(text))
        except ValueError:
            return value
    if isinstance(column_type, (Numeric, Float)):
        if isinstance(value, (int, float)):
            return value
        text = str(value).replace(",", "").replace("¥", "").strip()
        try:
            return float(text)
        except ValueError:
            return value
    if isinstance(column_type, Boolean):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    return value


class LoadOutcome:
    def __init__(self) -> None:
        self.written = 0
        self.skipped = 0
        self.rejected: list[dict[str, Any]] = []

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)


def insert_rows(
    schema: str,
    table_name: str,
    records: list[dict[str, Any]],
    strategy: str,
    conflict_key: str | None,
    run_id: uuid.UUID,
) -> LoadOutcome:
    """按冲突策略把行写入目标表，自动补 _sync_run_id / _synced_at。

    计数不依赖 psycopg 的 executemany rowcount（多值 INSERT 时可能是 -1）：
    先做批次内去重，再按策略预查已存在的冲突键，用集合差得出写入/跳过/拒绝数。
    """
    outcome = LoadOutcome()
    if not records:
        return outcome

    table = reflect_table(schema, table_name)
    key_columns = parse_conflict_key(conflict_key) if conflict_key else []
    for column in key_columns:
        if column not in table.c:
            raise AppError(
                codes.CONFLICT_KEY_ABSENT,
                "冲突键列不存在于目标表",
                f"conflict_key={conflict_key} column={column} missing in {schema}.{table_name}",
            )

    write_columns = [column for column in table.c.keys() if column in (records[0] or {})]
    write_columns += [column for column in AUDIT_COLUMNS if column in table.c]
    write_columns = list(dict.fromkeys(write_columns))

    synced_at = datetime.now(timezone.utc)
    stamped: list[dict[str, Any]] = []
    for record in records:
        row = {
            column: coerce_value(table.c[column].type, record.get(column))
            for column in write_columns
            if column in record
        }
        if "_sync_run_id" in table.c:
            row["_sync_run_id"] = run_id
        if "_synced_at" in table.c:
            row["_synced_at"] = synced_at
        # 原始载荷与行号只用于拒绝记录，不写进目标表
        if "__raw_payload__" in record:
            row["__raw_payload__"] = record["__raw_payload__"]
        if "__source_row_index__" in record:
            row["__source_row_index__"] = record["__source_row_index__"]
        stamped.append(row)

    # 1) 批次内重复键
    kept, batch_conflicts = _dedupe(stamped, key_columns, strategy)
    outcome.rejected.extend(batch_conflicts)
    if not kept:
        return outcome

    insert_stmt = pg_insert(table)

    # 2) 与目标表已存在的键求差
    if key_columns:
        existing = _existing_keys(table, key_columns, kept)
        if existing:
            survivors: list[dict[str, Any]] = []
            conflicted: list[dict[str, Any]] = []
            for row in kept:
                key = tuple(str(row.get(column)) for column in key_columns)
                (conflicted if key in existing else survivors).append(row)
            if strategy == ConflictStrategy.REJECT.value:
                for row in conflicted:
                    key = tuple(str(row.get(column)) for column in key_columns)
                    outcome.rejected.append(
                        {
                            "reason_code": "conflict_rejected",
                            "reason_detail": (
                                f"conflict_key={'+'.join(key_columns)} value={key} "
                                f"strategy=reject target={schema}.{table_name}"
                            ),
                            "raw_payload": row.get("__raw_payload__", row),
                            "source_row_index": row.get("__source_row_index__", 0),
                        }
                    )
                kept = survivors
            elif strategy == ConflictStrategy.SKIP.value:
                outcome.skipped = len(conflicted)
                kept = survivors

    if not kept:
        return outcome

    clean_rows = [
        {key: value for key, value in row.items() if not key.startswith("__")} for row in kept
    ]

    if key_columns and strategy == ConflictStrategy.OVERWRITE.value:
        update_columns = [column for column in clean_rows[0].keys() if column not in key_columns]
        update_map = {column: getattr(insert_stmt.excluded, column) for column in update_columns}
        insert_stmt = insert_stmt.on_conflict_do_update(index_elements=key_columns, set_=update_map)
        with _reflect_engine.begin() as conn:
            conn.execute(insert_stmt, clean_rows)
        outcome.written = len(clean_rows)
        return outcome

    if key_columns and strategy == ConflictStrategy.SKIP.value:
        insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=key_columns)

    with _reflect_engine.begin() as conn:
        conn.execute(insert_stmt, clean_rows)
    outcome.written = len(clean_rows)
    return outcome


def browse_target(
    schema: str,
    table_name: str,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    conflict_key: str | None = None,
) -> dict[str, Any]:
    table = reflect_table(schema, table_name)
    columns = [column.name for column in table.c]
    offset = max(page - 1, 0) * page_size
    stmt = select(table)
    count_stmt = select(text("count(*)")).select_from(table)
    # 有新近同步审计列时按写入时间倒序，让「刚同步进来的行」排在前面（BI 复核 _sync_run_id 用）
    if "_synced_at" in table.c:
        stmt = stmt.order_by(table.c["_synced_at"].desc().nulls_last())
    if q:
        search_columns = parse_conflict_key(conflict_key) if conflict_key else [
            column for column in columns if not column.startswith("_")
        ]
        search_columns = [column for column in search_columns if column in table.c]
        if search_columns:
            from sqlalchemy import String, cast, or_

            conditions = [
                cast(table.c[column], String).ilike(f"%{q}%") for column in search_columns
            ]
            stmt = stmt.where(or_(*conditions))
            count_stmt = count_stmt.where(or_(*conditions))
    stmt = stmt.limit(page_size).offset(offset)
    with _reflect_engine.connect() as conn:
        total = conn.execute(count_stmt).scalar_one()
        rows = conn.execute(stmt).mappings().all()
    return {
        "schema": schema,
        "table": table_name,
        "columns": table_columns(schema, table_name),
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "rows": [dict(row) for row in rows],
    }
