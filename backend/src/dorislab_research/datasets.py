"""Requested pages/ranges; filtering and sorting cover the entire dataset."""

import json
import math
from itertools import islice
from pathlib import Path
from typing import Any

from .dataset_cache import dataset
from .dataset_stream import clean, records


def rows(path: Path, request: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    request = request or {}
    offset = max(0, int(request.get("offset", 0)))
    limit = int(request.get("limit", 10000))
    if not 1 <= limit <= 10000:
        raise ValueError("图表每次最多读取 10000 行；请指定范围或先聚合数据")
    selected = request.get("columns")
    if selected is not None and (
        not isinstance(selected, list) or any(not isinstance(column, str) for column in selected)
    ):
        raise ValueError("请求的数据列无效")
    values = []
    size = 0
    end = offset + limit + (0 if "limit" in request else 1)
    for row in islice(records(path, selected), offset, end):
        if selected is not None and any(key not in row for key in selected):
            raise ValueError("请求的数据列不存在")
        value = {key: clean(row.get(key)) for key in (selected if selected is not None else row)}
        size += len(json.dumps(value, ensure_ascii=False).encode())
        if size > 8 * 1024 * 1024:
            raise ValueError("图表数据超过 8 MiB，请缩小读取范围或先聚合")
        values.append(value)
    if len(values) > limit:
        raise ValueError("图表超过 10000 行，请指定 offset/limit 范围或先聚合数据")
    return values


def table(path: Path, request: dict[str, Any]) -> dict[str, Any]:
    with dataset(path) as (db, columns):
        query = str(request.get("query", "")).casefold()
        total = db.execute(
            "SELECT count(*) FROM records WHERE instr(searchable,?)>0", (query,)
        ).fetchone()[0]
        size = min(100, max(1, int(request.get("page_size", 20))))
        number = max(1, min(int(request.get("page", 1)), math.ceil(total / size)))
        sort = request.get("sort")
        order = "position"
        if sort in columns:
            db.create_function("sort_group", 1, lambda s: comparable(json.loads(s).get(sort))[0])
            db.create_function("sort_value", 1, lambda s: comparable(json.loads(s).get(sort))[1])
            direction = "DESC" if request.get("descending") else "ASC"
            order = f"sort_group(content) {direction},sort_value(content) {direction},position"
        values = db.execute(
            f"SELECT content FROM records WHERE instr(searchable,?)>0 ORDER BY {order} "
            "LIMIT ? OFFSET ?",
            (query, size, (number - 1) * size),
        )
        return {
            "columns": columns,
            "rows": [json.loads(row[0]) for row in values],
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
