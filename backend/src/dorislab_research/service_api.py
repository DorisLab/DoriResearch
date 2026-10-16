import base64
import json
import mimetypes
import sqlite3
from collections.abc import Callable
from contextlib import closing
from typing import Any

from . import datasets, file_reads, library_queries, search_sync
from .database import connect
from .jobs import cancel, job, start
from .library import Library


def health(library: Library) -> dict[str, str]:
    with connect(library.root) as db:
        return {"schema": db.execute("SELECT version_num FROM alembic_version").fetchone()[0]}


def freeze(library: Library, args: dict[str, Any]) -> None:
    with connect(library.root) as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM jobs WHERE status IN ('running','queued')").fetchone():
            raise ValueError("仍有策略正在回测，请完成后启用工程")
        (library.root / "maintenance.json").write_text(json.dumps(args), encoding="utf-8")


def backup(library: Library) -> None:
    if not (library.root / "maintenance.json").is_file():
        raise ValueError("升级备份需要先暂停写入")
    with (
        connect(library.root) as source,
        closing(sqlite3.connect(library.root / "activation.sqlite3")) as destination,
    ):
        source.backup(destination)


def file_content(library: Library, args: dict[str, Any]) -> dict[str, str]:
    path = library.file(args["reference"], args["path"])
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("文件超过 8 MiB，请使用分段读取")
    return {
        "mime": mimetypes.guess_type(path)[0] or "application/octet-stream",
        "bytes": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def dispatch(library: Library, operation: str, args: dict[str, Any]) -> Any:
    reference = args.get("reference", {})
    operations: dict[str, Callable[[], Any]] = {
        "health": lambda: health(library),
        "search_changes": lambda: search_sync.changes(library, args),
        "file_chunk": lambda: file_reads.chunk(library, args),
        "table_preview": lambda: file_reads.table_preview(library, args),
        "freeze": lambda: freeze(library, args),
        "backup": lambda: backup(library),
        "list": lambda: library_queries.listing(
            library, args.get("query", ""), args.get("kind", "")
        ),
        "page": lambda: library_queries.page(library, args),
        "content": lambda: library.content(reference),
        "status": lambda: library_queries.status(library, reference),
        "archive": lambda: library_queries.archive(library, reference, args["archived"]),
        "archives": lambda: library_queries.archives(library),
        "delete": lambda: library_queries.delete(library, args["ids"]),
        "expire": lambda: library_queries.expire(library),
        "file": lambda: file_content(library, args),
        "text": lambda: file_reads.text(library, args),
        "rows": lambda: datasets.rows(library.file(reference, args["path"]), args),
        "table": lambda: datasets.table(library.file(reference, args["path"]), args),
        "backtest": lambda: start(library, reference, args),
        "job": lambda: job(library, args["id"]),
        "cancel_job": lambda: cancel(library, args["id"]),
        "results": lambda: [
            item
            for item in library_queries.listing(library, kind="run")
            if any(ref["id"] == reference["id"] for ref in item["references"])
        ],
    }
    if operation not in operations:
        raise ValueError("研究服务不支持此操作")
    return operations[operation]()
