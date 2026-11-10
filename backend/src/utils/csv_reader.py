"""CSV 读取：探测（分隔符/编码/字段清单）与批次读取，使用 pandas 做类型推断。"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import error_codes as codes
from src.utils.errors import AppError


def _open_text(path: str | Path, encoding: str = "utf-8") -> io.StringIO:
    raw = Path(path).read_bytes()
    for candidate in (encoding, "utf-8-sig", "gb18030", "latin-1"):
        try:
            return io.StringIO(raw.decode(candidate))
        except UnicodeDecodeError:
            continue
    raise AppError(codes.SOURCE_UNREACHABLE, "CSV 编码无法识别", f"path={path}")


def sniff_delimiter(path: str | Path, encoding: str = "utf-8") -> str:
    buffer = _open_text(path, encoding)
    sample = buffer.read(8192)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def probe_csv(path: str | Path, encoding: str = "utf-8", has_header: bool = True) -> dict[str, Any]:
    if not Path(path).exists():
        raise AppError(codes.SOURCE_UNREACHABLE, "CSV 文件不存在", f"path={path}")
    delimiter = sniff_delimiter(path, encoding)
    frame = pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        header=0 if has_header else None,
        dtype=str,
        keep_default_na=False,
        nrows=2000,
    )
    columns = [str(c) for c in frame.columns]
    return {
        "delimiter": delimiter,
        "encoding": encoding,
        "has_header": has_header,
        "columns": columns,
        "row_count": int(len(frame)),
        "sample": frame.head(20).to_dict(orient="records"),
    }


def read_csv_rows(
    path: str | Path,
    encoding: str = "utf-8",
    has_header: bool = True,
    delimiter: str | None = None,
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """批次读取为 dict 列表；列缺失时用空串兜底，保证转换阶段能给出 required_missing。"""
    if not Path(path).exists():
        raise AppError(codes.SOURCE_UNREACHABLE, "CSV 文件不存在", f"path={path}")
    sep = delimiter or sniff_delimiter(path, encoding)
    frame = pd.read_csv(
        path,
        sep=sep,
        encoding=encoding,
        header=0 if has_header else None,
        dtype=str,
        keep_default_na=False,
    )
    frame.columns = [str(c) for c in frame.columns]
    if columns:
        for column in columns:
            if column not in frame.columns:
                frame[column] = ""
        frame = frame[columns]
    return frame.to_dict(orient="records")
