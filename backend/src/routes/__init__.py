"""路由总装配。"""
from fastapi import APIRouter

from src.routes import (
    api_key,
    audit,
    auth,
    health,
    meta,
    mock,
    pipeline,
    rejected,
    run,
    source,
    target,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(mock.router)
api_router.include_router(source.router)
api_router.include_router(pipeline.router)
api_router.include_router(run.router)
api_router.include_router(rejected.router)
api_router.include_router(target.router)
api_router.include_router(api_key.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
