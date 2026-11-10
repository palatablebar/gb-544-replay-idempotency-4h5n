"""面向用户/日志的中文文案（前端另有一份 constants/messages.ts，需人工同步）。"""
from __future__ import annotations

from src.constants.enums import ConflictStrategy, RunStatus

CONFLICT_STRATEGY_HELP: dict[str, str] = {
    ConflictStrategy.SKIP.value: "目标表已有同键行时跳过，不报错也不覆盖，计入跳过数。",
    ConflictStrategy.OVERWRITE.value: "目标表已有同键行时整行覆盖，并刷新 _sync_run_id / _synced_at。",
    ConflictStrategy.REJECT.value: "目标表已有同键行时整行拒绝，写入拒绝记录待人工确认，不覆盖线上数据。",
}

RUN_STATUS_HINT: dict[str, str] = {
    RunStatus.QUEUED.value: "已入队，等待 worker 取管道锁。",
    RunStatus.RUNNING.value: "正在按阶段推进：抽取 → 转换 → 写入 → 校验。",
    RunStatus.SUCCEEDED.value: "全部行写入成功，水位线已推进。",
    RunStatus.PARTIAL.value: "主流程完成但有拒绝行，修完映射可以原样重放。",
    RunStatus.FAILED.value: "运行失败，可查看 error_message 与重试次数。",
    RunStatus.CANCELED.value: "运行被取消，未写入的部分不会回滚已提交批次。",
}

MSG_NO_NEW_DATA = "本批无新数据"
MSG_PIPELINE_LOCKED = "这条管道正在跑，去看当前运行"
MSG_QUOTA_EXCEEDED = "并发运行数已达上限，请稍后再试"
MSG_VIEWER_READONLY = "当前是只读角色（BI），不能触发运行或重放"
MSG_MAPPING_REQUIRED = "至少需要一条字段映射才能保存"
MSG_MAPPING_EMPTY_TARGET = "目标列不能为空"

# 前端空态文案（后端在 /api/meta/ui-text 中返回同一份，避免两处不一致）
EMPTY_STATES: dict[str, str] = {
    "sources": "先登记一个源：CSV 直接拖入，PostgreSQL 填 schema + 表名，Mock REST 用内置示例地址；登记后可以点『探测』看字段",
    "pipelines": "还没有管道。选一个源 → 填目标表 → 去映射页配字段，三步就能跑第一次全量",
    "runs": "还没有运行记录。在管道行尾点『运行一次』，或给管道设一个 cron",
}
