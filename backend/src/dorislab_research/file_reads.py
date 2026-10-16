"""Bounded file transport with a revision check across pages."""

import base64
import mimetypes
from typing import Any

from .dataset_cache import stamp
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
        "start": start,
        "rows": [[str(row.get(key, "")) for key in page["columns"]] for row in page["rows"]],
        "next": {"offset": next_row, "row": next_row, "revision": version}
        if next_row < page["total"]
        else None,
    }
