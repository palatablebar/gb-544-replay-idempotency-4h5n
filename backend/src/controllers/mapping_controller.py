"""映射 controller：读取、批量保存、试运行、从探测字段一键填充。"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.data_source import DataSource
from src.models.user import User
from src.schemas.mapping import MappingBulkSave, MappingPreviewRequest
from src.services import audit_service, load_service, mapping_service, pipeline_service
from src.utils.logger import get_logger

logger = get_logger("syncmesh.mapping.controller")


def list_mappings(pipeline_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    return {
        "pipeline_id": pipeline_id,
        "target_columns": [c["name"] for c in load_service.table_columns(pipeline.target_schema, pipeline.target_table)],
        "items": mapping_service.list_mappings(db, pipeline.id),
    }


def save_mappings(
    pipeline_id: str,
    payload: MappingBulkSave,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("mappings:write")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    items = mapping_service.save_mappings(db, pipeline, payload.mappings)
    audit_service.record(
        db,
        action="mapping.save",
        entity_type="SyncPipeline",
        entity_id=str(pipeline.id),
        actor_id=str(user.id),
        payload={"rows": len(items)},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return {"items": items, "ok": True}


def preview_mappings(
    pipeline_id: str,
    payload: MappingPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    return mapping_service.preview(db, pipeline, payload.mappings, limit=payload.limit)


def fill_from_probe(pipeline_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    source = db.get(DataSource, pipeline.source_id)
    source_columns = (source.probe_result_json or {}).get("columns", []) if source else []
    target_columns = [
        column["name"]
        for column in load_service.table_columns(pipeline.target_schema, pipeline.target_table)
    ]
    return {"items": mapping_service.fill_from_probe(source_columns, target_columns)}
