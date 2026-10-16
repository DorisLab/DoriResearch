"""Content deltas, including direct edits to persistent reading materials."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from .database import connect
from .dataset_cache import stamp
from .library import Library, local_file
from .library_queries import summary

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


def changes(library: Library, request: dict[str, Any]) -> dict[str, Any]:
    with connect(library.root) as db:
        db.execute("BEGIN IMMEDIATE")
        refresh(db, library)
        generation = db.execute(
            "SELECT value FROM settings WHERE key='search_generation'"
        ).fetchone()[0]
        maximum = db.execute("SELECT coalesce(max(sequence),0) FROM search_changes").fetchone()[0]
        cursor = max(0, int(request.get("cursor", 0)))
        reset = request.get("generation") != generation or cursor > maximum
        if reset:
            cursor = 0
        changed = db.execute(
            """SELECT c.sequence,c.id,e.* ,s.text AS file_text
            FROM search_changes c LEFT JOIN entries e ON e.id=c.id
            LEFT JOIN search_files s ON s.id=c.id
            WHERE c.sequence>? ORDER BY c.sequence LIMIT 50""",
            (cursor,),
        ).fetchall()
        documents = [document(dict(row)) for row in changed]
        next_cursor = changed[-1]["sequence"] if changed else maximum
        return {
            "generation": generation,
            "reset": reset,
            "cursor": next_cursor,
            "has_more": next_cursor < maximum,
            "documents": documents,
        }


def document(row: dict[str, Any]) -> dict[str, Any]:
    visible = row["kind"] and row["archived_at"] is None and row["deleted_at"] is None
    return {
        "id": row["id"],
        "item": summary(row) if visible else None,
        "text": "\n".join(str(row.get(k) or "") for k in ("title", "summary", "file_text"))
        if visible
        else "",
    }
