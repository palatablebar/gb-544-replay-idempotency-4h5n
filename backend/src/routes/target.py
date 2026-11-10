from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import target_controller
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/targets", tags=["targets"])


@router.get("")
def list_tables(db: Session = Depends(get_db), user=Depends(get_current_user)) -> dict:
    return target_controller.list_tables(db, user)


@router.get("/{schema}/{table}")
def browse(
    schema: str,
    table: str,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    return target_controller.browse(schema, table, page, page_size, q, db, user)
