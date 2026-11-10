from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import source_controller
from src.schemas.source import SourceCreate, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(db: Session = Depends(get_db), user=Depends(source_controller.get_current_user)) -> dict:
    return source_controller.list_sources(db, user)


@router.post("")
def create_source(payload: SourceCreate, request: Request, db: Session = Depends(get_db), user=Depends(source_controller.require_permission("sources:write"))) -> dict:
    return source_controller.create_source(payload, request, db, user)


@router.post("/upload")
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    source_type: str = Form(default="csv"),
    db: Session = Depends(get_db),
    user=Depends(source_controller.require_permission("sources:write")),
) -> dict:
    return source_controller.upload_file(request, file, source_type, db, user)


@router.get("/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db), user=Depends(source_controller.get_current_user)) -> dict:
    return source_controller.get_source(source_id, db, user)


@router.post("/{source_id}/probe")
def probe(source_id: str, db: Session = Depends(get_db), user=Depends(source_controller.get_current_user)) -> dict:
    return source_controller.probe_source(source_id, db, user)


@router.get("/{source_id}/sample")
def sample(source_id: str, limit: int = 20, db: Session = Depends(get_db), user=Depends(source_controller.get_current_user)) -> dict:
    return source_controller.sample_source(source_id, limit, db, user)


@router.put("/{source_id}")
def update_source(source_id: str, payload: SourceUpdate, request: Request, db: Session = Depends(get_db), user=Depends(source_controller.require_permission("sources:write"))) -> dict:
    return source_controller.update_source(source_id, payload, request, db, user)


@router.delete("/{source_id}")
def delete_source(source_id: str, request: Request, db: Session = Depends(get_db), user=Depends(source_controller.require_permission("sources:write"))) -> dict:
    return source_controller.delete_source(source_id, request, db, user)
