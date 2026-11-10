"""目标表 controller：表清单、列类型、分页浏览与按 conflict_key 搜索。"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.config.settings import settings
from src.middlewares.auth import get_current_user
from src.models.sync_pipeline import SyncPipeline
from src.models.user import User
from src.schemas.target import serialize_target_row
from src.services import load_service
from src.utils.errors import AppError, not_found

TARGET_TABLES = ("store_sales", "members", "channel_orders", "members_source")


def list_tables(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    pipelines = db.query(SyncPipeline).all()
    pipeline_by_table = {
        f"{pipeline.target_schema}.{pipeline.target_table}": pipeline for pipeline in pipelines
    }
    items = []
    for table in TARGET_TABLES:
        full_name = f"{settings.target_schema}.{table}"
        try:
            columns = load_service.table_columns(settings.target_schema, table)
            browse = load_service.browse_target(settings.target_schema, table, page=1, page_size=1)
            total = browse["total"]
        except AppError:
            columns, total = [], 0
        pipeline = pipeline_by_table.get(full_name)
        items.append(
            {
                "schema": settings.target_schema,
                "table": table,
                "full_name": full_name,
                "columns": columns,
                "row_count": total,
                "pipeline_id": str(pipeline.id) if pipeline else None,
                "pipeline_name": pipeline.name if pipeline else None,
                "conflict_key": pipeline.conflict_key if pipeline else None,
            }
        )
    return {"items": items}


def browse(
    schema: str,
    table: str,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    pipeline = (
        db.query(SyncPipeline)
        .filter(SyncPipeline.target_schema == schema, SyncPipeline.target_table == table)
        .first()
    )
    try:
        result = load_service.browse_target(
            schema, table, page=page, page_size=min(page_size, 100), q=q,
            conflict_key=pipeline.conflict_key if pipeline else None,
        )
    except AppError as exc:
        if exc.code == "TARGET_TABLE_MISSING":
            raise not_found("TargetTable", f"{schema}.{table}")
        raise
    result["rows"] = [serialize_target_row(row) for row in result["rows"]]
    result["pipeline_id"] = str(pipeline.id) if pipeline else None
    return result
