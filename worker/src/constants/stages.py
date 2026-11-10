"""阶段常量与前端阶段步进文案的唯一来源（新增阶段必须同步 backend/constants/enums.py 与前端）。"""
from __future__ import annotations

STAGE_ORDER: list[str] = ["probe", "extract", "transform", "load", "verify"]

STAGE_LABELS: dict[str, str] = {
    "probe": "探测源",
    "extract": "抽取",
    "transform": "转换",
    "load": "写入",
    "verify": "校验",
}

STAGE_DONE_HINT: dict[str, str] = {
    "probe": "已确认源可达与字段清单",
    "extract": "已按水位线过滤出本批行",
    "transform": "已按映射逐列转换",
    "load": "已按冲突策略写入目标表",
    "verify": "已完成行数账目与必填校验",
}
