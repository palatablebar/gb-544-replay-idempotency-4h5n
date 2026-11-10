"""管道服务：创建、更新、保存校验、启停、复制、删除。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import PipelineStatus, SyncMode
from src.models.data_source import DataSource
from src.models.field_mapping import FieldMapping
from src.models.sync_pipeline import SyncPipeline
from src.models.sync_run import SyncRun
from src.schemas.pipeline import serialize_pipeline
from src.services import load_service, mapping_service, verify_service
from src.utils.errors import AppError, not_found


def get_pipeline(db: Session, pipeline_id: Any) -> SyncPipeline:
    pipeline = db.get(SyncPipeline, pipeline_id)
    if pipeline is None:
        raise not_found("SyncPipeline", pipeline_id)
    return pipeline


def list_pipelines(db: Session) -> list[SyncPipeline]:
    return db.query(SyncPipeline).order_by(SyncPipeline.created_at.asc()).all()


def create_pipeline(db: Session, owner_id: str, payload: dict[str, Any]) -> SyncPipeline:
    source = db.get(DataSource, payload["source_id"])
    if source is None:
        raise AppError(codes.NOT_FOUND, "数据源不存在", f"source_id={payload['source_id']}")
    data_schema = payload.get("target_schema") or "target"
    target_table = payload.get("target_table") or ""
    load_service.reflect_table(data_schema, target_table)  # 目标表不存在直接报错
    pipeline = SyncPipeline(
        owner_id=owner_id,
        source_id=source.id,
        name=payload["name"],
        target_schema=data_schema,
        target_table=target_table,
        sync_mode=payload.get("sync_mode", SyncMode.INCREMENTAL.value),
        watermark_column=payload.get("watermark_column"),
        conflict_strategy=payload.get("conflict_strategy", "skip"),
        conflict_key=payload.get("conflict_key"),
        schedule_cron=payload.get("schedule_cron"),
        batch_size=int(payload.get("batch_size", 100)),
        status=PipelineStatus.DRAFT.value,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def update_pipeline(db: Session, pipeline: SyncPipeline, payload: dict[str, Any]) -> SyncPipeline:
    for field in (
        "name",
        "sync_mode",
        "watermark_column",
        "conflict_strategy",
        "conflict_key",
        "schedule_cron",
        "batch_size",
        "status",
    ):
        if field in payload and payload[field] is not None:
            setattr(pipeline, field, payload[field])
    if payload.get("target_table"):
        load_service.reflect_table(pipeline.target_schema, payload["target_table"])
        pipeline.target_table = payload["target_table"]
    if payload.get("target_schema"):
        pipeline.target_schema = payload["target_schema"]
    pipeline.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def validate_pipeline(db: Session, pipeline: SyncPipeline) -> dict[str, Any]:
    mappings = mapping_service.mapping_dicts(db, pipeline.id)
    verify_service.validate_pipeline_config(
        pipeline_id=pipeline.id,
        sync_mode=pipeline.sync_mode,
        watermark_column=pipeline.watermark_column,
        conflict_strategy=pipeline.conflict_strategy,
        conflict_key=pipeline.conflict_key,
        target_schema=pipeline.target_schema,
        target_table=pipeline.target_table,
        mappings=mappings,
    )
    return {"ok": True, "mappings": len(mappings)}


def set_status(db: Session, pipeline: SyncPipeline, status: str) -> SyncPipeline:
    if status == PipelineStatus.ACTIVE.value:
        validate_pipeline(db, pipeline)
        if not pipeline.schedule_cron:
            raise AppError(
                codes.VALIDATION_ERROR,
                "启用调度前请先填写 cron 表达式",
                f"pipeline={pipeline.id} schedule_cron empty",
            )
    pipeline.status = status
    pipeline.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def duplicate_pipeline(db: Session, pipeline: SyncPipeline, new_name: str | None = None) -> SyncPipeline:
    clone = SyncPipeline(
        owner_id=pipeline.owner_id,
        source_id=pipeline.source_id,
        name=new_name or f"{pipeline.name}-copy",
        target_schema=pipeline.target_schema,
        target_table=pipeline.target_table,
        sync_mode=pipeline.sync_mode,
        watermark_column=pipeline.watermark_column,
        conflict_strategy=pipeline.conflict_strategy,
        conflict_key=pipeline.conflict_key,
        schedule_cron=pipeline.schedule_cron,
        batch_size=pipeline.batch_size,
        status=PipelineStatus.DRAFT.value,
    )
    db.add(clone)
    db.flush()
    for mapping in (
        db.query(FieldMapping)
        .filter(FieldMapping.pipeline_id == pipeline.id)
        .order_by(FieldMapping.order_index.asc())
        .all()
    ):
        db.add(
            FieldMapping(
                pipeline_id=clone.id,
                source_field=mapping.source_field,
                target_column=mapping.target_column,
                transform_type=mapping.transform_type,
                transform_config_json=mapping.transform_config_json,
                default_value=mapping.default_value,
                is_required=mapping.is_required,
                order_index=mapping.order_index,
            )
        )
    db.commit()
    db.refresh(clone)
    return clone


def delete_pipeline(db: Session, pipeline: SyncPipeline) -> None:
    db.query(FieldMapping).filter(FieldMapping.pipeline_id == pipeline.id).delete()
    db.delete(pipeline)
    db.commit()


def serialize_many(db: Session, pipelines: list[SyncPipeline]) -> list[dict[str, Any]]:
    from src.schemas.run import serialize_run

    source_ids = {pipeline.source_id for pipeline in pipelines}
    sources = {
        source.id: source
        for source in db.query(DataSource).filter(DataSource.id.in_(source_ids)).all()
    }
    result = []
    for pipeline in pipelines:
        source = sources.get(pipeline.source_id)
        last_run = (
            db.query(SyncRun)
            .filter(SyncRun.pipeline_id == pipeline.id)
            .order_by(SyncRun.created_at.desc())
            .first()
        )
        mapping_count = (
            db.query(FieldMapping).filter(FieldMapping.pipeline_id == pipeline.id).count()
        )
        result.append(
            serialize_pipeline(
                pipeline,
                source_name=source.name if source else None,
                source_type=source.source_type if source else None,
                source_status=source.status if source else None,
                last_run=serialize_run(last_run, pipeline_name=pipeline.name) if last_run else None,
                mapping_count=mapping_count,
            )
        )
    return result
