"""字段转换注册表 + 按映射逐列转换（worker 与 backend 共用同一份实现）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from src.constants.enums import ReasonCode, TransformType
from src.constants.transforms import TransformConfigError, validate_transform_config

TransformFn = Callable[[Any, dict[str, Any], dict[str, Any]], Any]


class TransformFailure(Exception):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(detail)


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def _t_trim(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    return _as_text(value).strip()


def _t_upper(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    return _as_text(value).strip().upper()


def _t_lower(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    return _as_text(value).strip().lower()


def _t_date_format(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    raw = _as_text(value).strip()
    if raw == "":
        return None
    src_fmt = config.get("from", "%Y/%m/%d")
    dst_fmt = config.get("to", "%Y-%m-%d")
    for fmt in (src_fmt, "%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime(dst_fmt)
        except ValueError:
            continue
    raise TransformFailure(
        ReasonCode.TRANSFORM_FAILED.value,
        f"field=date_format observed='{raw}' expected_format='{src_fmt}'",
    )


def _t_number_cast(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    raw = _as_text(value).strip()
    if raw == "":
        return None
    strip_chars = str(config.get("strip", "¥,元,")).split(",")
    cleaned = raw
    for char in strip_chars:
        if char:
            cleaned = cleaned.replace(char, "")
    # 千分位 / 全角逗号 / 货币符号一律清理，再尝试数值解析
    for char in ("，", ",", " ", "¥", "￥", "元"):
        cleaned = cleaned.replace(char, "")
    cleaned = cleaned.strip()
    try:
        number = float(cleaned)
    except ValueError as exc:
        raise TransformFailure(
            ReasonCode.TYPE_MISMATCH.value,
            f"field=number_cast observed='{raw}' reason=not_a_number",
        ) from exc
    places = int(config.get("decimal_places", 2))
    return round(number, places)


def _t_concat(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    fields = config.get("fields") or []
    if not fields:
        raise TransformFailure(ReasonCode.TRANSFORM_FAILED.value, "field=concat reason=fields_empty")
    separator = str(config.get("separator", "-"))
    parts = [_as_text(row.get(field, "")).strip() for field in fields]
    return separator.join(parts)


def _t_default(value: Any, config: dict[str, Any], row: dict[str, Any]) -> Any:
    raw = _as_text(value).strip()
    if raw != "":
        return raw
    return config.get("value", "")


TRANSFORM_REGISTRY: dict[str, TransformFn] = {
    TransformType.TRIM.value: _t_trim,
    TransformType.UPPER.value: _t_upper,
    TransformType.LOWER.value: _t_lower,
    TransformType.DATE_FORMAT.value: _t_date_format,
    TransformType.NUMBER_CAST.value: _t_number_cast,
    TransformType.CONCAT.value: _t_concat,
    TransformType.DEFAULT.value: _t_default,
}


def apply_transform(transform_type: str, config: dict[str, Any], value: Any, row: dict[str, Any]) -> Any:
    fn = TRANSFORM_REGISTRY.get(transform_type)
    if fn is None:
        raise TransformFailure(ReasonCode.TRANSFORM_FAILED.value, f"unknown transform_type={transform_type}")
    try:
        return fn(value, config, row)
    except TransformFailure:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TransformFailure(
            ReasonCode.TRANSFORM_FAILED.value,
            f"transform={transform_type} error={exc}",
        ) from exc


def transform_row(
    row: dict[str, Any],
    mappings: list[dict[str, Any]],
    source_row_index: int = 0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """返回 (目标行, 拒绝项列表)。拒绝项含 reason_code / reason_detail / raw_payload。"""
    mapped: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    for mapping in mappings:
        source_field = mapping["source_field"]
        target_column = mapping["target_column"]
        transform_type = mapping.get("transform_type") or TransformType.TRIM.value
        config = mapping.get("transform_config") or {}
        default_value = mapping.get("default_value")
        is_required = bool(mapping.get("is_required"))

        raw = row.get(source_field)
        raw_text = "" if raw is None else str(raw).strip()

        if raw_text == "" and default_value not in (None, ""):
            raw = default_value
            raw_text = str(default_value).strip()

        if transform_type == TransformType.DEFAULT.value and raw_text == "":
            config = {**config, "value": config.get("value") or default_value or ""}

        try:
            converted = apply_transform(transform_type, config, raw, row)
        except TransformFailure as failure:
            failures.append(
                _failure(failure.reason_code, failure.detail, row, source_row_index)
            )
            continue

        if converted is None or (isinstance(converted, str) and converted.strip() == ""):
            if is_required:
                failures.append(
                    _failure(
                        ReasonCode.REQUIRED_MISSING.value,
                        f"field={target_column} source_field={source_field} observed=''",
                        row,
                        source_row_index,
                    )
                )
                continue
            mapped[target_column] = None
            continue

        mapped[target_column] = converted
    return mapped, failures


def _failure(reason_code: str, detail: str, row: dict[str, Any], source_row_index: int) -> dict[str, Any]:
    return {
        "reason_code": reason_code,
        "reason_detail": detail,
        "raw_payload": row,
        "source_row_index": source_row_index,
    }


def validate_mapping_config(transform_type: str, config: dict[str, Any] | None) -> dict[str, Any]:
    try:
        return validate_transform_config(transform_type, config)
    except TransformConfigError as exc:
        raise TransformFailure(ReasonCode.TRANSFORM_FAILED.value, str(exc)) from exc
