"""后端枚举定义（前端 frontend/src/constants/*.ts 有对应的第二份定义，靠 README 对照表同步）。"""
from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    CSV = "csv"
    JSONL = "jsonl"
    POSTGRES_TABLE = "postgres_table"
    MOCK_REST = "mock_rest"


class SourceStatus(str, Enum):
    UNTESTED = "untested"
    OK = "ok"
    UNREACHABLE = "unreachable"


class SyncMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELED = "canceled"

    @classmethod
    def terminal(cls) -> set[str]:
        return {cls.SUCCEEDED.value, cls.PARTIAL.value, cls.FAILED.value, cls.CANCELED.value}


class ConflictStrategy(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    REJECT = "reject"


class TransformType(str, Enum):
    TRIM = "trim"
    UPPER = "upper"
    LOWER = "lower"
    DATE_FORMAT = "date_format"
    NUMBER_CAST = "number_cast"
    CONCAT = "concat"
    DEFAULT = "default"


class PipelineStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    API = "api"


class Stage(str, Enum):
    PROBE = "probe"
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VERIFY = "verify"

    @classmethod
    def ordered(cls) -> list[str]:
        return [cls.PROBE.value, cls.EXTRACT.value, cls.TRANSFORM.value, cls.LOAD.value, cls.VERIFY.value]


class ReasonCode(str, Enum):
    REQUIRED_MISSING = "required_missing"
    TYPE_MISMATCH = "type_mismatch"
    TRANSFORM_FAILED = "transform_failed"
    CONFLICT_REJECTED = "conflict_rejected"
    CONSTRAINT_VIOLATION = "constraint_violation"


class TargetSchema(str, Enum):
    STAGING = "staging"
    TARGET = "target"


class ActorKind(str, Enum):
    USER = "user"
    API_KEY = "api_key"


# 各枚举的中文展示名（后端 formatters 与接口文案共用）
ENUM_LABELS: dict[str, dict[str, str]] = {
    "SourceType": {
        "csv": "CSV 文件",
        "jsonl": "JSONL 日志",
        "postgres_table": "PostgreSQL 表",
        "mock_rest": "Mock REST 接口",
    },
    "SourceStatus": {"untested": "未探测", "ok": "连通", "unreachable": "不可达"},
    "SyncMode": {"full": "全量", "incremental": "增量"},
    "RunStatus": {
        "queued": "排队中",
        "running": "运行中",
        "succeeded": "成功",
        "partial": "部分成功",
        "failed": "失败",
        "canceled": "已取消",
    },
    "ConflictStrategy": {"skip": "跳过", "overwrite": "覆盖", "reject": "拒绝"},
    "TransformType": {
        "trim": "去空格",
        "upper": "转大写",
        "lower": "转小写",
        "date_format": "日期格式化",
        "number_cast": "数值转换",
        "concat": "字段拼接",
        "default": "默认值填充",
    },
    "PipelineStatus": {"draft": "草稿", "active": "已启用", "paused": "已暂停", "error": "异常"},
    "TriggerType": {"manual": "手动", "schedule": "调度", "api": "接口"},
    "Stage": {"probe": "探测", "extract": "抽取", "transform": "转换", "load": "写入", "verify": "校验"},
    "ReasonCode": {
        "required_missing": "必填字段缺失",
        "type_mismatch": "类型不匹配",
        "transform_failed": "转换失败",
        "conflict_rejected": "冲突被拒绝",
        "constraint_violation": "约束冲突",
    },
}
