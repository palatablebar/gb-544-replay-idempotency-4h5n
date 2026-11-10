"""Mock REST 连接器：真实 HTTP 分页拉取 + 5xx 退避重试 + 限流尊重。"""
from __future__ import annotations

import time
from typing import Any

import httpx

from src.constants import error_codes as codes
from src.utils.errors import AppError
from src.utils.logger import get_logger
from worker_src.constants.tuning import REST_PAGE_RETRY_ATTEMPTS, REST_TIMEOUT_SECONDS
from worker_src.config.settings import settings

logger = get_logger("syncmesh.worker.rest")


def _endpoint(config: dict[str, Any]) -> str:
    endpoint = config.get("endpoint") or "/api/mock/rest/shop_orders"
    base = settings.mock_rest_base_url.rstrip("/")
    if endpoint.startswith("http"):
        return endpoint
    if not endpoint.startswith("/api"):
        endpoint = f"/api{endpoint}"
    return f"{base}{endpoint}"


def read(config: dict[str, Any], columns: list[str] | None = None) -> list[dict[str, Any]]:
    url = _endpoint(config)
    page_size = int(config.get("page_size", 50))
    rows: list[dict[str, Any]] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = _fetch_with_retry(url, page, page_size)
        rows.extend(payload.get("items", []))
        total_pages = int(payload.get("total_pages", 1))
        page += 1
    logger.info("rest read rows=%s pages=%s url=%s", len(rows), total_pages, url)
    return rows


def _fetch_with_retry(url: str, page: int, page_size: int) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, REST_PAGE_RETRY_ATTEMPTS + 1):
        try:
            response = httpx.get(
                url, params={"page": page, "page_size": page_size}, timeout=REST_TIMEOUT_SECONDS
            )
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", "1"))
                time.sleep(min(retry_after, 5))
                raise AppError(
                    codes.MOCK_REST_RATE_LIMITED, "Mock REST 触发限流", f"page={page}"
                )
            if response.status_code >= 500:
                raise AppError(
                    codes.SOURCE_UNREACHABLE,
                    "Mock REST 返回 5xx",
                    f"page={page} status={response.status_code}",
                )
            response.raise_for_status()
            return response.json()
        except (AppError, httpx.HTTPError) as exc:
            last_error = exc
            logger.warning(
                "rest page retry page=%s attempt=%s error=%s", page, attempt, exc
            )
            time.sleep(min(0.4 * (2 ** (attempt - 1)), 4))
    raise AppError(
        codes.SOURCE_UNREACHABLE,
        "Mock REST 多次重试仍失败",
        f"page={page} error={last_error}",
    )
