"""Content deltas, including direct edits to persistent reading materials."""

from typing import Any

from .database import connect
from .library import Library
from .library_queries import summary
from .search_files import refresh


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
