"""Explicit host storage: SQLite recovery remains owned by DoriResearch."""

import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from .database import connect


def backup(root: Path, target: Path) -> None:
    if not (root / "maintenance.json").is_file():
        raise ValueError("升级备份需要先暂停写入")
    if not target.is_absolute() or target.resolve().is_relative_to(root.resolve()):
        raise ValueError("备份必须使用客户端提供的独立绝对路径")
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=target.parent, suffix=".sqlite")
    os.close(handle)
    try:
        with connect(root) as source, closing(sqlite3.connect(temporary)) as destination:
            source.backup(destination)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def restore(root: Path, source: Path) -> None:
    if not (root / "maintenance.json").is_file():
        raise ValueError("恢复需要先暂停写入")
    if not source.is_absolute() or source.resolve().is_relative_to(root.resolve()):
        raise ValueError("恢复必须使用客户端登记的独立备份")
    with (
        closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as saved,
        closing(sqlite3.connect(root / "library.sqlite")) as destination,
    ):
        if saved.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("备份数据库损坏，原库已保留")
        saved.backup(destination)
