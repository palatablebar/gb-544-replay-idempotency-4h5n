from fastapi import APIRouter

from src.controllers import meta_controller

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/enums")
def enums() -> dict:
    return meta_controller.enums()


@router.get("/ui-text")
def ui_text() -> dict:
    return meta_controller.ui_text()
