"""TransformType 的参数校验规则（与前端 constants/transforms.ts 的 TransformParamSpec 对应）。"""
from __future__ import annotations

from typing import Any

from src.constants.enums import TransformType

# 每种转换的参数说明：key -> (是否必填, 默认值, 说明)
TRANSFORM_PARAM_SPECS: dict[str, dict[str, dict[str, Any]]] = {
    TransformType.TRIM.value: {},
    TransformType.UPPER.value: {},
    TransformType.LOWER.value: {},
    TransformType.DATE_FORMAT.value: {
        "from": {"required": True, "default": "%Y/%m/%d", "desc": "源格式（strptime）"},
        "to": {"required": True, "default": "%Y-%m-%d", "desc": "目标格式（strftime）"},
    },
    TransformType.NUMBER_CAST.value: {
        "decimal_places": {"required": False, "default": 2, "desc": "保留小数位"},
        "strip": {"required": False, "default": "¥,元, ", "desc": "需要剔除的字符（逗号分隔）"},
    },
    TransformType.CONCAT.value: {
        "fields": {"required": True, "default": [], "desc": "参与拼接的源字段列表"},
        "separator": {"required": False, "default": "-", "desc": "分隔符"},
    },
    TransformType.DEFAULT.value: {
        "value": {"required": False, "default": "", "desc": "为空时填入的值"},
    },
}


class TransformConfigError(ValueError):
    pass


def validate_transform_config(transform_type: str, config: dict[str, Any] | None) -> dict[str, Any]:
    """校验并补默认值；不合法抛 TransformConfigError（service 层包成 AppError）。"""
    if transform_type not in TRANSFORM_PARAM_SPECS:
        raise TransformConfigError(f"unknown transform_type={transform_type}")
    spec = TRANSFORM_PARAM_SPECS[transform_type]
    config = dict(config or {})
    for key, rule in spec.items():
        if rule["required"] and (key not in config or config[key] in (None, "", [])):
            raise TransformConfigError(f"transform {transform_type} requires param '{key}'")
        if key not in config and rule["default"] is not None:
            config[key] = rule["default"]
    return config
