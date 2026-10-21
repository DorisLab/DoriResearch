"""Shared incremental reading-material index for list and global search."""

import json
import sqlite3
from pathlib import Path

from .dataset_cache import stamp
from .library import Library, local_file

TEXT_LIMIT = 1024 * 1024


def files(root: Path) -> tuple[str, list[Path]]:
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    safe = [local_file(root, p.relative_to(root).as_posix()) for p in paths]
    return json.dumps([(p.relative_to(root).as_posix(), stamp(p)) for p in safe]), safe


def refresh(db: sqlite3.Connection, library: Library) -> None:
    entries = db.execute("""SELECT e.id,e.directory,s.stamp FROM entries e
        LEFT JOIN search_files s ON s.id=e.id
        WHERE e.deleted_at IS NULL AND e.archived_at IS NULL""").fetchall()
    for entry in entries:
        root = library.root / "files" / entry["directory"]
        fingerprint, paths = files(root)
        if fingerprint == entry["stamp"]:
            continue
        # Large data arrays are queried as tables, not copied into full-text search.
        texts = [p.relative_to(root).as_posix() for p in paths]
        texts.extend(
            p.read_text(encoding="utf-8-sig")
            for p in paths
            if p.suffix.lower() in (".md", ".txt") and p.stat().st_size <= TEXT_LIMIT
        )
        if files(root)[0] != fingerprint:
            raise ValueError("研究文件正在改变，请稍后重试搜索")
        db.execute(
            "INSERT OR REPLACE INTO search_files VALUES (?,?,?)",
            (entry["id"], fingerprint, "\n".join(texts)),
        )
        db.execute("DELETE FROM search_changes WHERE id=?", (entry["id"],))
        db.execute("INSERT INTO search_changes(id) VALUES (?)", (entry["id"],))
