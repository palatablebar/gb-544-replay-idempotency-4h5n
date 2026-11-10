"""内置 Mock REST 数据源：分页、限流、偶发 5xx，以及『电商业补推批次』开关。

数据是确定性生成的，seed、前端提示与 README 引用的是同一套数值：
- 基础数据 3 页 × 50 行 = 150 行（order_id 1001..1150）
- 补推批次 27 行：4 个 order_id 各重复 4 次（12 行冲突）+ 3 行 member_id 为空 + 8 行正常
"""
from __future__ import annotations

from typing import Any

from src.constants.limits import MOCK_REST_BASE_ROWS, MOCK_REST_FAILURE_EVERY, MOCK_REST_PAGE_SIZE
from src.utils.redis_client import get_redis

PUSH_FLAG_KEY = "mock:shop_orders:push"
REQ_COUNTER_KEY = "mock:shop_orders:req"
RATE_KEY = "mock:shop_orders:rate"

VALID_MEMBERS = ["M0001", "M0002", "M0003", "M0007", "M0012", "M0031", "M0044", "M0102"]
CHANNELS = ["mall", "mini", "app"]
ORDER_STATUS = ["paid", "shipped", "refunded"]


def _base_order(index: int) -> dict[str, Any]:
    order_id = 1001 + index
    return {
        "order_id": order_id,
        "member_id": VALID_MEMBERS[index % len(VALID_MEMBERS)],
        "amount": f"{(index % 47) * 12.5 + 19.9:.2f}",
        "channel": CHANNELS[index % len(CHANNELS)],
        "order_status": ORDER_STATUS[index % len(ORDER_STATUS)],
        "updated_at": f"2026-11-{8 + (index % 2):02d} {9 + (index % 9):02d}:{(index * 7) % 60:02d}:00",
    }


def base_rows() -> list[dict[str, Any]]:
    return [_base_order(i) for i in range(MOCK_REST_BASE_ROWS)]


def push_batch_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # 12 行冲突：4 个 order_id 各补推 4 次，第一次落库，其余 3 次命中 batch 内重复键 → conflict_rejected
    for offset, order_id in enumerate([1151, 1152, 1153, 1154]):
        for repeat in range(4):
            rows.append(
                {
                    "order_id": order_id,
                    "member_id": VALID_MEMBERS[(offset + repeat) % len(VALID_MEMBERS)],
                    "amount": f"{88.0 + offset + repeat / 10:.2f}",
                    "channel": "mall",
                    "order_status": "paid",
                    "updated_at": "2026-11-10 01:12:00",
                }
            )
    # 3 行必填缺失：member_id 为空 → required_missing
    for offset, order_id in enumerate([1155, 1156, 1157]):
        rows.append(
            {
                "order_id": order_id,
                "member_id": "",
                "amount": f"{120.0 + offset:.2f}",
                "channel": "mini",
                "order_status": "paid",
                "updated_at": "2026-11-10 01:20:00",
            }
        )
    # 8 行正常新增
    for offset, order_id in enumerate(range(1158, 1166)):
        rows.append(
            {
                "order_id": order_id,
                "member_id": VALID_MEMBERS[(offset + 3) % len(VALID_MEMBERS)],
                "amount": f"{260.0 + offset * 3:.2f}",
                "channel": "app",
                "order_status": "paid",
                "updated_at": "2026-11-10 01:24:00",
            }
        )
    return rows


def push_enabled() -> bool:
    try:
        return get_redis().get(PUSH_FLAG_KEY) == "1"
    except Exception:
        return False


def set_push_enabled(enabled: bool) -> None:
    client = get_redis()
    if enabled:
        client.set(PUSH_FLAG_KEY, "1")
    else:
        client.delete(PUSH_FLAG_KEY)


def all_rows() -> list[dict[str, Any]]:
    rows = base_rows()
    if push_enabled():
        rows.extend(push_batch_rows())
    return rows


def paginate(page: int, page_size: int = MOCK_REST_PAGE_SIZE) -> dict[str, Any]:
    rows = all_rows()
    total = len(rows)
    page = max(int(page), 1)
    page_size = max(min(int(page_size), 200), 1)
    total_pages = max((total + page_size - 1) // page_size, 1)
    start = (page - 1) * page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "items": rows[start : start + page_size],
        "push_batch": push_enabled(),
    }


def should_fail_once() -> bool:
    """每 N 次请求返回一次 500，用于验证重试链路（Redis 计数）。"""
    try:
        counter = get_redis().incr(REQ_COUNTER_KEY)
        return counter % MOCK_REST_FAILURE_EVERY == 0
    except Exception:
        return False
