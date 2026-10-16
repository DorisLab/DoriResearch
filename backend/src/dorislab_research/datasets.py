"""Decode content data, not market-data discovery or an analysis pipeline."""

import csv
import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

# Load native extensions on the service's main thread, before request workers start.
import pyarrow.parquet as pq


def rows(path: Path) -> list[dict[str, Any]]:
    match path.suffix.lower():
        case ".parquet":
            values = cast(Callable[..., Any], pq.read_table)(path).to_pylist()
        case ".csv" | ".tsv":
            with path.open(encoding="utf-8-sig", newline="") as file:
                values = list(
                    csv.DictReader(file, delimiter="\t" if path.suffix == ".tsv" else ",")
                )
        case ".json":
            values = json.loads(path.read_text(encoding="utf-8"))
        case _:
            raise ValueError("数据文件支持 JSON、CSV、TSV 和 Parquet")
    if not isinstance(values, list) or any(not isinstance(row, dict) for row in values):
        raise ValueError("数据须为包含列名的记录数组")
    return [{str(key): clean(value) for key, value in row.items()} for row in values]


def clean(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def table(path: Path, request: dict[str, Any]) -> dict[str, Any]:
    values = rows(path)
    columns = list(dict.fromkeys(key for row in values for key in row))
    query = str(request.get("query", "")).casefold()
    values = [row for row in values if query in " ".join(str(v) for v in row.values()).casefold()]
    sort = request.get("sort")
    if sort in columns:
        values.sort(
            key=lambda row: comparable(row.get(sort)), reverse=bool(request.get("descending"))
        )
    total = len(values)
    number = max(1, min(int(request.get("page", 1)), math.ceil(total / 20)))
    return {
        "columns": columns,
        "rows": values[(number - 1) * 20 : number * 20],
        "total": total,
        "page": number,
    }


def comparable(value: Any) -> tuple[int, Any]:
    if value is None:
        return (2, "")
    try:
        return (0, float(value))
    except (ValueError, TypeError):
        return (1, str(value).casefold())
