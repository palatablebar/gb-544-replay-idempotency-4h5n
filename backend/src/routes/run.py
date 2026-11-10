from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import run_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.schemas.run import ReplayRequest, TriggerRequest

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(
    status: str | None = None,
    pipeline_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    return run_controller.list_runs(status, pipeline_id, limit, db, user)


@router.post("/trigger")
def trigger(payload: TriggerRequest, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("runs:trigger"))) -> dict:
    return run_controller.trigger_run(payload, request, db, user)


@router.post("/trigger/api-key")
def trigger_with_api_key(payload: TriggerRequest, request: Request, db: Session = Depends(get_db), actor=Depends(run_controller.trigger_actor)) -> dict:
    return run_controller.trigger_run_with_api_key(payload, request, actor, db)


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return run_controller.get_run(run_id, db, user)


@router.post("/{run_id}/cancel")
def cancel(run_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("runs:trigger"))) -> dict:
    return run_controller.cancel_run(run_id, request, db, user)


@router.post("/{run_id}/replay")
def replay(run_id: str, payload: ReplayRequest, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("runs:replay"))) -> dict:
    return run_controller.replay(run_id, payload, request, db, user)


@router.post("/{run_id}/replay/api-key")
def replay_api_key(run_id: str, payload: ReplayRequest, request: Request, db: Session = Depends(get_db), actor=Depends(run_controller.replay_actor)) -> dict:
    from src.services import run_service
    from src.constants.enums import ActorKind
    from src.services import audit_service

    run = run_service.get_run(db, run_id)
    result = run_service.replay_records(
        db, run=run, rejected_ids=payload.rejected_ids, reason_code=payload.reason_code,
        actor=actor.user, actor_kind=ActorKind.API_KEY.value,
    )
    audit_service.record(
        db, action="run.replay", entity_type="SyncRun", entity_id=str(run.id),
        actor_id=str(actor.user_id), actor_kind=ActorKind.API_KEY.value,
        payload={"queued": result["queued"], "channel": "api_key"},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return result
