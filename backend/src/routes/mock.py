from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.controllers import meta_controller

router = APIRouter(prefix="/mock/rest", tags=["mock"])


@router.get("/shop_orders")
def shop_orders(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> JSONResponse:
    return meta_controller.mock_shop_orders(request, page, page_size)


@router.get("/shop_orders/state")
def push_state() -> dict:
    return meta_controller.mock_push_state()


@router.post("/shop_orders/push")
def push_batch() -> dict:
    return meta_controller.mock_set_push(True)


@router.delete("/shop_orders/push")
def reset_push() -> dict:
    return meta_controller.mock_set_push(False)
