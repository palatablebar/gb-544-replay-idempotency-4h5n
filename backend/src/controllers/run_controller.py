"""运行 controller：时间线、详情、取消、触发（JWT / API Key 双通道）、重放。"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.enums import ActorKind, TriggerType
from src.middlewares.api_key import ApiActor, replay_actor, trigger_actor
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.run import ReplayRequest, TriggerRequest, serialize_run
from src.services import audit_service, pipeline_service, quota_service, run_service
from src.utils.errors import AppError


def list_runs(
    status: str | None = None,
    pipeline_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    items = run_service.list_runs(db, status=status, pipeline_id=pipeline_id, limit=min(limit, 200))
    return {"items": items, "quota": quota_service.summary(db, user)}


def get_run(run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return run_service.run_detail(db, run_id)


def cancel_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("runs:trigger")),
) -> dict:
    run = run_service.cancel_run(db, run_id)
    audit_service.record(
        db,
        action="run.cancel",
        entity_type="SyncRun",
        entity_id=str(run.id),
        actor_id=str(user.id),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_run(run)


def trigger_run(
    payload: TriggerRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("runs:trigger")),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, payload.pipeline_id)
    trigger_type = payload.trigger_type if payload.trigger_type in ("manual", "api") else TriggerType.MANUAL.value
    run = run_service.create_run(db, pipeline=pipeline, user=user, trigger_type=trigger_type)
    audit_service.record(
        db,
        action="run.trigger",
        entity_type="SyncRun",
        entity_id=str(run.id),
        actor_id=str(user.id),
        actor_kind=ActorKind.USER.value,
        payload={"pipeline": pipeline.name, "channel": "jwt"},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_run(run, pipeline_name=pipeline.name)


def trigger_run_with_api_key(
    payload: TriggerRequest,
    request: Request,
    actor: ApiActor = Depends(trigger_actor),
    db: Session = Depends(get_db),
) -> dict:
    pipeline = pipeline_service.get_pipeline(db, payload.pipeline_id)
    run = run_service.create_run(
        db,
        pipeline=pipeline,
        user=actor.user,
        trigger_type=TriggerType.API.value,
        actor_kind=ActorKind.API_KEY.value,
    )
    audit_service.record(
        db,
        action="run.trigger",
        entity_type="SyncRun",
        entity_id=str(run.id),
        actor_id=str(actor.user_id),
        actor_kind=ActorKind.API_KEY.value,
        payload={"pipeline": pipeline.name, "channel": "api_key"},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_run(run, pipeline_name=pipeline.name)


def replay(
    run_id: str,
    payload: ReplayRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("runs:replay")),
) -> dict:
    run = run_service.get_run(db, run_id)
    result = run_service.replay_records(
        db,
        run=run,
        rejected_ids=payload.rejected_ids,
        reason_code=payload.reason_code,
        actor=user,
    )
    audit_service.record(
        db,
        action="run.replay",
        entity_type="SyncRun",
        entity_id=str(run.id),
        actor_id=str(user.id),
        payload={"queued": result["queued"], "reason_code": payload.reason_code, "batch_id": result.get("batch_id")},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return result


def replay_with_api_key(
    run_id: str,
    payload: ReplayRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("runs:replay")),
) -> dict:
    return replay(run_id, payload, request, db, user)
