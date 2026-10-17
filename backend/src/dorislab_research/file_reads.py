"""Bounded file transport with a revision check across pages."""

import base64
import json
import mimetypes
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pyarrow.parquet as pq

from .dataset_cache import stamp
from .dataset_stream import clean
from .datasets import table
from .library import Library


def chunk(library: Library, args: dict[str, Any]) -> dict[str, Any]:
    path = library.file(args["reference"], args["path"])
    version = stamp(path)
    if args.get("revision", version) != version:
        raise ValueError("文件已改变，请重新载入")
    size = path.stat().st_size
    offset = int(args.get("offset", 0))
    length = int(args.get("length", 256 * 1024))
    if offset < 0 or not 0 < length <= 1024 * 1024:
        raise ValueError("文件读取范围无效")
    with path.open("rb") as file:
        file.seek(offset)
        content = file.read(length)
    if stamp(path) != version:
        raise ValueError("文件已改变，请重新载入")
    return {
        "mime": mimetypes.guess_type(path)[0] or "application/octet-stream",
        "bytes": base64.b64encode(content).decode("ascii"),
        "size": size,
        "revision": version,
        "offset": offset,
    }


def text(library: Library, args: dict[str, Any]) -> str:
    path = library.file(args["reference"], args["path"])
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("内嵌配置文本超过 1 MiB，请改用数据文件及范围读取")
    with path.open("rb") as file:
        content = file.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise ValueError("内嵌配置文本超过 1 MiB")
    return content.decode("utf-8-sig")


def table_preview(library: Library, args: dict[str, Any]) -> dict[str, Any]:
    path = library.file(args["reference"], args["path"])
    return _table_preview(path, args)


def path_table_preview(args: dict[str, Any]) -> dict[str, Any]:
    """Host-only local path, resolved by the account-aware desktop command."""
    path = Path(args["path"])
    if not path.is_absolute() or path.suffix.lower() != ".parquet":
        raise ValueError("请选择本地 Parquet 文件")
    version = stamp(path)
    cursor = args.get("cursor") or {}
    if cursor.get("revision", version) != version:
        raise ValueError("文件已改变，请重新载入表格")
    start = int(cursor.get("row", 0))
    if start < 0 or start % 100:
        raise ValueError("表格读取位置无效")
    with cast(Callable[..., Any], pq.ParquetFile)(path) as file:
        headers = file.schema_arrow.names
        if len(headers) > 256:
            raise ValueError("表头超过 256 列，请在系统中打开")
        rows: list[list[str]] = []
        size = 0
        for row in parquet_rows(file, start):
            cells = ["" if row.get(key) is None else str(clean(row[key])) for key in headers]
            size += len(json.dumps(cells, ensure_ascii=False).encode())
            if size > 4 * 1024 * 1024:
                raise ValueError("单页内容超过 4 MiB，请在系统中打开")
            rows.append(cells)
            if len(rows) == 100:
                break
        next_row = start + len(rows)
        more = next_row < file.metadata.num_rows
    if stamp(path) != version:
        raise ValueError("文件已改变，请重新载入表格")
    return {
        "headers": headers,
        "rows": rows,
        "start": start + 1,
        "next": {"offset": next_row, "row": next_row, "revision": version} if more else None,
    }


def parquet_rows(file: Any, skip: int) -> Iterator[dict[str, Any]]:
    for group in range(file.num_row_groups):
        count = file.metadata.row_group(group).num_rows
        if skip >= count:
            skip -= count
            continue
        for batch in file.iter_batches(batch_size=100, row_groups=[group]):
            if skip >= batch.num_rows:
                skip -= batch.num_rows
                continue
            yield from batch.slice(skip).to_pylist()
            skip = 0


def _table_preview(path: Path, args: dict[str, Any]) -> dict[str, Any]:
    version = stamp(path)
    cursor = args.get("cursor") or {}
    if cursor.get("revision", version) != version:
        raise ValueError("文件已改变，请重新载入表格")
    start = int(cursor.get("row", 0))
    if start < 0 or start % 100:
        raise ValueError("表格读取位置无效")
    page = table(path, {"page": start // 100 + 1, "page_size": 100})
    next_row = start + len(page["rows"])
    if stamp(path) != version:
        raise ValueError("文件已改变，请重新载入表格")
    return {
        "headers": page["columns"],
        "start": start + 1,
        "rows": [[str(row.get(key, "")) for key in page["columns"]] for row in page["rows"]],
        "next": {"offset": next_row, "row": next_row, "revision": version}
        if next_row < page["total"]
        else None,
    }
