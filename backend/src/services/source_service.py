"""数据源服务：登记、探测、抽样、更新、删除（被引用时拒绝并说明引用者）。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import SourceStatus, SourceType
from src.models.data_source import DataSource
from src.models.sync_pipeline import SyncPipeline
from src.services import extract_service
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger

logger = get_logger("syncmesh.source")

SOURCE_TYPE_CONFIG_KEYS: dict[str, list[str]] = {
    SourceType.CSV.value: ["upload_path", "delimiter", "has_header", "encoding"],
    SourceType.JSONL.value: ["upload_path", "encoding"],
    SourceType.POSTGRES_TABLE.value: ["dsn_alias", "schema", "table"],
    SourceType.MOCK_REST.value: ["endpoint", "page_size", "cursor_field"],
}


def _validate_config(source_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if source_type not in SOURCE_TYPE_CONFIG_KEYS:
        raise AppError(
            codes.VALIDATION_ERROR, "未知数据源类型", f"source_type={source_type}"
        )
    merged = dict(config or {})
    if source_type in (SourceType.CSV.value, SourceType.JSONL.value):
        upload_path = merged.get("upload_path")
        if upload_path:
            path = Path(upload_path)
            if not path.is_absolute():
                path = Path(settings.source_dir) / upload_path
            if not path.exists():
                raise AppError(
                    codes.SOURCE_UNREACHABLE,
                    "上传文件不存在",
                    f"upload_path={upload_path}",
                )
    if source_type == SourceType.POSTGRES_TABLE.value:
        merged.setdefault("dsn_alias", "default")
        merged.setdefault("schema", "target")
        if not merged.get("table"):
            raise AppError(
                codes.VALIDATION_ERROR, "请填写 PostgreSQL 表名", "config.table empty"
            )
    if source_type == SourceType.MOCK_REST.value:
        merged.setdefault("endpoint", "/api/mock/rest/shop_orders")
        merged.setdefault("page_size", 50)
        merged.setdefault("cursor_field", "order_id")
    return merged


def create_source(
    db: Session, *, owner_id: str, name: str, source_type: str, config: dict[str, Any]
) -> DataSource:
    existing = db.query(DataSource).filter(DataSource.name == name).one_or_none()
    if existing is not None:
        raise AppError(
            codes.VALIDATION_ERROR, "同名数据源已存在", f"name={name} already exists"
        )
    source = DataSource(
        owner_id=owner_id,
        name=name,
        source_type=source_type,
        config_json=_validate_config(source_type, config),
        status=SourceStatus.UNTESTED.value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    logger.info("source registered id=%s name=%s type=%s", source.id, name, source_type)
    return source


def get_source(db: Session, source_id: str) -> DataSource:
    try:
        uuid_value = UUID(str(source_id))
    except (ValueError, AttributeError):
        raise not_found("DataSource", source_id)
    source = db.get(DataSource, uuid_value)
    if source is None:
        raise not_found("DataSource", source_id)
    return source


def list_sources(db: Session) -> list[DataSource]:
    return db.query(DataSource).order_by(DataSource.created_at.asc()).all()


def referenced_pipelines(db: Session, source_id: UUID) -> list[dict[str, Any]]:
    rows = (
        db.query(SyncPipeline)
        .filter(SyncPipeline.source_id == source_id)
        .order_by(SyncPipeline.name.asc())
        .all()
    )
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "target_full_name": f"{row.target_schema}.{row.target_table}",
        }
        for row in rows
    ]


def probe_source(db: Session, source_id: str) -> dict[str, Any]:
    source = get_source(db, source_id)
    try:
        result = extract_service.probe_source(source.source_type, source.config_json or {})
    except AppError as exc:
        source.status = SourceStatus.UNREACHABLE.value
        source.last_probed_at = datetime.now(timezone.utc)
        db.commit()
        logger.warning("source probe fail id=%s code=%s detail=%s", source.id, exc.code, exc.detail)
        raise
    source.status = SourceStatus.OK.value
    source.last_probed_at = datetime.now(timezone.utc)
    source.probe_result_json = result
    db.commit()
    db.refresh(source)
    logger.info(
        "source probe ok id=%s fields=%s", source.id, len(result.get("columns", []))
    )
    return result


def sample_rows(db: Session, source_id: str, limit: int = 20) -> dict[str, Any]:
    source = get_source(db, source_id)
    config = source.config_json or {}
    probe = source.probe_result_json or {}
    columns = probe.get("columns") or None
    rows = extract_service.read_source_rows(source.source_type, config, columns=columns)
    return {
        "columns": columns or (list(rows[0].keys()) if rows else []),
        "rows": rows[:limit],
        "total": len(rows),
    }


def update_source(db: Session, source_id: str, *, name: str | None, config: dict[str, Any] | None) -> DataSource:
    source = get_source(db, source_id)
    if name and name != source.name:
        duplicated = db.query(DataSource).filter(DataSource.name == name).one_or_none()
        if duplicated is not None:
            raise AppError(codes.VALIDATION_ERROR, "同名数据源已存在", f"name={name}")
        source.name = name
    if config is not None:
        source.config_json = _validate_config(source.source_type, {**source.config_json, **config})
        source.status = SourceStatus.UNTESTED.value
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, source_id: str) -> None:
    source = get_source(db, source_id)
    references = referenced_pipelines(db, source.id)
    if references:
        names = "、".join(item["name"] for item in references)
        raise AppError(
            codes.SOURCE_IN_USE,
            f"数据源被 {len(references)} 条管道引用（{names}），请先删除或改绑这些管道",
            f"DataSource[id={source.id}] delete failed: referenced by {names}",
            extra={"referenced_pipelines": references},
        )
    db.delete(source)
    db.commit()
