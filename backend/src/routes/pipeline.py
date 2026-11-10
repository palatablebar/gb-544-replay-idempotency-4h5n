from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import mapping_controller, pipeline_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.schemas.mapping import MappingBulkSave, MappingPreviewRequest
from src.schemas.pipeline import PipelineCreate, PipelineUpdate

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("")
def list_pipelines(db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return pipeline_controller.list_pipelines(db, user)


@router.post("")
def create_pipeline(payload: PipelineCreate, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("pipelines:write"))) -> dict:
    return pipeline_controller.create_pipeline(payload, request, db, user)


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return pipeline_controller.get_pipeline(pipeline_id, db, user)


@router.put("/{pipeline_id}")
def update_pipeline(pipeline_id: str, payload: PipelineUpdate, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("pipelines:write"))) -> dict:
    return pipeline_controller.update_pipeline(pipeline_id, payload, request, db, user)


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("pipelines:delete"))) -> dict:
    return pipeline_controller.delete_pipeline(pipeline_id, request, db, user)


@router.post("/{pipeline_id}/validate")
def validate_pipeline(pipeline_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return pipeline_controller.validate_pipeline(pipeline_id, db, user)


@router.post("/{pipeline_id}/activate")
def activate(pipeline_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("pipelines:write"))) -> dict:
    return pipeline_controller.activate_pipeline(pipeline_id, request, db, user)


@router.post("/{pipeline_id}/pause")
def pause(pipeline_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("pipelines:write"))) -> dict:
    return pipeline_controller.pause_pipeline(pipeline_id, request, db, user)


@router.post("/{pipeline_id}/trigger")
def trigger(pipeline_id: str, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("runs:trigger"))) -> dict:
    return pipeline_controller.trigger_pipeline(pipeline_id, request, db, user)


@router.post("/{pipeline_id}/duplicate")
def duplicate(pipeline_id: str, db: Session = Depends(get_db), user=Depends(require_permission("pipelines:write"))) -> dict:
    return pipeline_controller.duplicate_pipeline(pipeline_id, db, user)


@router.get("/{pipeline_id}/mappings")
def list_mappings(pipeline_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return mapping_controller.list_mappings(pipeline_id, db, user)


@router.put("/{pipeline_id}/mappings")
def save_mappings(pipeline_id: str, payload: MappingBulkSave, request: Request, db: Session = Depends(get_db), user=Depends(require_permission("mappings:write"))) -> dict:
    return mapping_controller.save_mappings(pipeline_id, payload, request, db, user)


@router.post("/{pipeline_id}/mappings/preview")
def preview(pipeline_id: str, payload: MappingPreviewRequest, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return mapping_controller.preview_mappings(pipeline_id, payload, db, user)


@router.get("/{pipeline_id}/mappings/fill")
def fill(pipeline_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return mapping_controller.fill_from_probe(pipeline_id, db, user)
