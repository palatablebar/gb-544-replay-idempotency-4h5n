"""数据源 controller：登记、上传、探测、抽样、更新、删除。"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import ActorKind, SourceType
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.source import SourceCreate, SourceUpdate, serialize_source
from src.services import audit_service, source_service
from src.utils.checksum import sha256_file
from src.utils.errors import AppError
from src.utils.logger import get_logger

logger = get_logger("syncmesh.source.controller")


def list_sources(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    sources = source_service.list_sources(db)
    return {
        "items": [
            serialize_source(source, source_service.referenced_pipelines(db, source.id))
            for source in sources
        ]
    }


def create_source(
    payload: SourceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sources:write")),
) -> dict:
    source = source_service.create_source(
        db,
        owner_id=str(user.id),
        name=payload.name,
        source_type=payload.source_type,
        config=payload.config,
    )
    audit_service.record(
        db,
        action="source.create",
        entity_type="DataSource",
        entity_id=str(source.id),
        actor_id=str(user.id),
        actor_kind=ActorKind.USER.value,
        payload={"name": source.name, "source_type": source.source_type},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_source(source)


def upload_file(
    request: Request,
    file: UploadFile = File(...),
    source_type: str = Form(default=SourceType.CSV.value),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sources:write")),
) -> dict:
    target_dir = Path(settings.source_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or "upload.csv").name
    destination = target_dir / filename
    with destination.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    size_mb = destination.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        destination.unlink(missing_ok=True)
        raise AppError(
            codes.UPLOAD_TOO_LARGE,
            f"文件超过 {settings.max_upload_mb}MB 限制",
            f"size_mb={size_mb:.1f}",
        )
    checksum = sha256_file(destination)
    logger.info("file uploaded name=%s checksum=%s", filename, checksum[:12])
    return {
        "upload_path": str(destination),
        "filename": filename,
        "checksum": checksum,
        "size_bytes": destination.stat().st_size,
        "source_type": source_type,
    }


def get_source(source_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    source = source_service.get_source(db, source_id)
    return serialize_source(source, source_service.referenced_pipelines(db, source.id))


def probe_source(source_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    result = source_service.probe_source(db, source_id)
    return {"ok": True, "probe": result}


def sample_source(
    source_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return source_service.sample_rows(db, source_id, limit=min(limit, 20))


def update_source(
    source_id: str,
    payload: SourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sources:write")),
) -> dict:
    source = source_service.update_source(db, source_id, name=payload.name, config=payload.config)
    audit_service.record(
        db,
        action="source.update",
        entity_type="DataSource",
        entity_id=str(source.id),
        actor_id=str(user.id),
        payload=payload.model_dump(exclude_none=True),
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return serialize_source(source)


def delete_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sources:write")),
) -> dict:
    source = source_service.get_source(db, source_id)
    name = source.name
    source_service.delete_source(db, source_id)
    audit_service.record(
        db,
        action="source.delete",
        entity_type="DataSource",
        entity_id=str(source_id),
        actor_id=str(user.id),
        payload={"name": name},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return {"ok": True}
