"""四类数据源统一抽取接口：探测（probe）与全量读取。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import SourceType
from src.utils import csv_reader, jsonl_reader, mock_rest
from src.utils.errors import AppError


def resolve_source_path(config: dict[str, Any]) -> Path:
    upload_path = config.get("upload_path") or ""
    if not upload_path:
        raise AppError(codes.SOURCE_UNREACHABLE, "CSV/JSONL 源缺少 upload_path", "config.upload_path empty")
    path = Path(upload_path)
    if not path.exists():
        # 允许相对 SOURCE_DIR 的写法
        path = Path(settings.source_dir) / Path(upload_path).name
    if not path.exists():
        raise AppError(codes.SOURCE_UNREACHABLE, "上传文件不存在", f"path={path}")
    return path


def probe_source(source_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if source_type == SourceType.CSV.value:
        path = resolve_source_path(config)
        return csv_reader.probe_csv(
            path,
            encoding=config.get("encoding", "utf-8"),
            has_header=bool(config.get("has_header", True)),
        )
    if source_type == SourceType.JSONL.value:
        path = resolve_source_path(config)
        return jsonl_reader.probe_jsonl(path)
    if source_type == SourceType.POSTGRES_TABLE.value:
        return _probe_pg_table(config)
    if source_type == SourceType.MOCK_REST.value:
        payload = mock_rest.paginate(1, int(config.get("page_size", 50)))
        columns = list(payload["items"][0].keys()) if payload["items"] else []
        return {
            "delimiter": None,
            "encoding": "utf-8",
            "has_header": True,
            "columns": columns,
            "row_count": payload["total"],
            "sample": payload["items"][:20],
            "total_pages": payload["total_pages"],
            "page": payload["page"],
            "page_size": payload["page_size"],
            "note": f"共 {payload['total_pages']} 页",
        }
    raise AppError(codes.SOURCE_UNREACHABLE, "未知数据源类型", f"source_type={source_type}")


def _probe_pg_table(config: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import inspect, text

    from src.config.database import engine

    schema = config.get("schema") or "target"
    table = config.get("table")
    if not table:
        raise AppError(codes.SOURCE_UNREACHABLE, "PostgreSQL 源缺少 table", "config.table empty")
    inspector = inspect(engine)
    if not inspector.has_table(table, schema=schema):
        raise AppError(
            codes.SOURCE_UNREACHABLE, "PostgreSQL 表不存在", f"{schema}.{table} not found"
        )
    columns = [col["name"] for col in inspector.get_columns(table, schema=schema)]
    with engine.connect() as conn:
        rows = conn.execute(
            text(f'SELECT * FROM "{schema}"."{table}" LIMIT 20')
        ).mappings().all()
        total = conn.execute(text(f'SELECT count(*) FROM "{schema}"."{table}"')).scalar_one()
    return {
        "delimiter": None,
        "encoding": "utf-8",
        "has_header": True,
        "columns": columns,
        "row_count": int(total),
        "sample": [dict(row) for row in rows],
        "dsn_alias": config.get("dsn_alias", "default"),
    }


def read_source_rows(
    source_type: str,
    config: dict[str, Any],
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """全量抽取（增量过滤在 pipelines/incremental.py 里做）。"""
    if source_type == SourceType.CSV.value:
        return csv_reader.read_csv_rows(
            resolve_source_path(config),
            encoding=config.get("encoding", "utf-8"),
            has_header=bool(config.get("has_header", True)),
            delimiter=config.get("delimiter"),
            columns=columns,
        )
    if source_type == SourceType.JSONL.value:
        return jsonl_reader.read_jsonl_rows(resolve_source_path(config), columns=columns)
    if source_type == SourceType.POSTGRES_TABLE.value:
        return _read_pg_rows(config, columns)
    if source_type == SourceType.MOCK_REST.value:
        return _read_rest_rows(config)
    raise AppError(codes.SOURCE_UNREACHABLE, "未知数据源类型", f"source_type={source_type}")


def _read_pg_rows(config: dict[str, Any], columns: list[str] | None) -> list[dict[str, Any]]:
    from sqlalchemy import text

    from src.config.database import engine

    schema = config.get("schema") or "target"
    table = config.get("table")
    if not table:
        raise AppError(codes.SOURCE_UNREACHABLE, "PostgreSQL 源缺少 table", "config.table empty")
    column_sql = ", ".join(f'"{c}"' for c in columns) if columns else "*"
    with engine.connect() as conn:
        rows = conn.execute(text(f'SELECT {column_sql} FROM "{schema}"."{table}"')).mappings().all()
    return [dict(row) for row in rows]


def _read_rest_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    page_size = int(config.get("page_size", mock_rest.MOCK_REST_PAGE_SIZE))
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = mock_rest.paginate(page, page_size)
        rows.extend(payload["items"])
        if page >= payload["total_pages"]:
            break
        page += 1
    return rows
