"""Disposable, disk-backed query cache; source files remain authoritative."""

import json
import sqlite3
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .dataset_stream import MAX_RECORD, clean, records

_lock = threading.RLock()
_cache: OrderedDict[Path, tuple[str, tempfile.TemporaryDirectory[str], list[str]]] = OrderedDict()


def stamp(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}"


def build(path: Path, db: sqlite3.Connection) -> list[str]:
    columns: dict[str, None] = {}
    db.execute("CREATE TABLE records (position INTEGER PRIMARY KEY, content TEXT, searchable TEXT)")
    with db:
        for index, row in enumerate(records(path)):
            row = {str(key): clean(value) for key, value in row.items()}
            columns.update(dict.fromkeys(row))
            content = json.dumps(row, ensure_ascii=False, allow_nan=False)
            if len(content.encode()) > MAX_RECORD:
                raise ValueError("单条数据超过 4 MiB，请将大字段拆为独立文件")
            db.execute(
                "INSERT INTO records VALUES (?,?,?)",
                (index, content, " ".join(str(v) for v in row.values()).casefold()),
            )
    return list(columns)


@contextmanager
def dataset(path: Path) -> Iterator[tuple[sqlite3.Connection, list[str]]]:
    path = path.resolve()
    with _lock:
        version = stamp(path)
        previous = _cache.get(path)
        if previous and previous[0] != version:
            _cache.pop(path)[1].cleanup()
            previous = None
        if not previous:
            directory = tempfile.TemporaryDirectory(prefix="doriresearch-table-")
            db = sqlite3.connect(Path(directory.name) / "rows.sqlite3")
            try:
                columns = build(path, db)
                if stamp(path) != version:
                    raise ValueError("数据文件已改变，请重新读取")
            except BaseException:
                db.close()
                directory.cleanup()
                raise
            db.close()
            _cache[path] = (version, directory, columns)
            while len(_cache) > 4:
                _cache.popitem(last=False)[1][1].cleanup()
        _cache.move_to_end(path)
        _, directory, columns = _cache[path]
        connection = sqlite3.connect(Path(directory.name) / "rows.sqlite3")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("PRAGMA cache_size=-8192")
        try:
            yield connection, columns
            if stamp(path) != version:
                raise ValueError("数据文件已改变，请重新读取")
        finally:
            connection.close()
