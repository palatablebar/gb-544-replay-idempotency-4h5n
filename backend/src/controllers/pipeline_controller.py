"""管道 controller：列表、创建、更新、启停、触发、复制、删除。"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.enums import ActorKind, PipelineStatus, TriggerType
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.pipeline import PipelineCreate, PipelineUpdate
from src.schemas.run import serialize_run
from src.services import audit_service, pipeline_service, run_service, scheduler_service
from src.utils.errors import AppError
from src.utils.logger import get_logger

logger = get_logger("syncmesh.pipeline.controller")


def list_pipelines(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    pipelines = pipeline_service.list_pipelines(db)
    return {"items": pipeline_service.serialize_many(db, pipelines)}


def get_pipeline(pipeline_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    return pipeline_service.serialize_many(db, [pipeline])[0]


def create_pipeline(
    payload: PipelineCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pipelines:write")),
) -> dict:
    pipeline = pipeline_service.create_pipeline(db, str(user.id), payload.model_dump(by_alias=True))
    audit_service.record(
        db,
        action="pipeline.create",
        entity_type="SyncPipeline",
        entity_id=str(pipeline.id),
        actor_id=str(user.id),
        payload={"name": pipeline.name, "target": f"{pipeline.target_schema}.{pipeline.target_table}"},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return pipeline_service.serialize_many(db, [pipeline])[0]


def update_pipeline(
    pipeline_id: str,
    payload: PipelineUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pipelines:write")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    if payload.schedule_cron and not scheduler_service.validate_cron(payload.schedule_cron):
        raise AppError("VALIDATION_ERROR", "cron 表达式不合法", payload.schedule_cron)
    pipeline = pipeline_service.update_pipeline(db, pipeline, payload.model_dump(by_alias=True, exclude_none=True))
    audit_service.record(
        db,
        action="pipeline.update",
        entity_type="SyncPipeline",
        entity_id=str(pipeline.id),
        actor_id=str(user.id),
        payload=payload.model_dump(by_alias=True, exclude_none=True),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return pipeline_service.serialize_many(db, [pipeline])[0]


def validate_pipeline(pipeline_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    return pipeline_service.validate_pipeline(db, pipeline)


def activate_pipeline(
    pipeline_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pipelines:write")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    pipeline = pipeline_service.set_status(db, pipeline, PipelineStatus.ACTIVE.value)
    audit_service.record(
        db,
        action="pipeline.activate",
        entity_type="SyncPipeline",
        entity_id=str(pipeline.id),
        actor_id=str(user.id),
        payload={"cron": pipeline.schedule_cron},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return pipeline_service.serialize_many(db, [pipeline])[0]


def pause_pipeline(
    pipeline_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pipelines:write")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    pipeline = pipeline_service.set_status(db, pipeline, PipelineStatus.PAUSED.value)
    audit_service.record(
        db,
        action="pipeline.pause",
        entity_type="SyncPipeline",
        entity_id=str(pipeline.id),
        actor_id=str(user.id),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return pipeline_service.serialize_many(db, [pipeline])[0]


def trigger_pipeline(
    pipeline_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("runs:trigger")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    run = run_service.create_run(
        db, pipeline=pipeline, user=user, trigger_type=TriggerType.MANUAL.value
    )
    audit_service.record(
        db,
        action="run.trigger",
        entity_type="SyncRun",
        entity_id=str(run.id),
        actor_id=str(user.id),
        actor_kind=ActorKind.USER.value,
        payload={"pipeline_id": str(pipeline.id), "pipeline": pipeline.name},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_run(run, pipeline_name=pipeline.name)


def duplicate_pipeline(
    pipeline_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pipelines:write")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    clone = pipeline_service.duplicate_pipeline(db, pipeline)
    return pipeline_service.serialize_many(db, [clone])[0]


def delete_pipeline(
    pipeline_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("pipelines:delete")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, pipeline_id)
    name = pipeline.name
    pipeline_service.delete_pipeline(db, pipeline)
    audit_service.record(
        db,
        action="pipeline.delete",
        entity_type="SyncPipeline",
        entity_id=str(pipeline_id),
        actor_id=str(user.id),
        payload={"name": name},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return {"ok": True}
