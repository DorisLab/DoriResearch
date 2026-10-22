"""Reading links and current related items, separate from pinned research evidence."""

import json
import sqlite3
from typing import Any
from urllib.parse import quote


def markdown_link(label: str, url: str) -> str:
    label = label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    return f"[{label.replace(chr(10), ' ')}](<{url}>)"


def links(record: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    url = f"dorislab://artifact/{record['kind']}/{record['id']}/{record['revision']}"
    return {
        "url": url,
        "markdown": markdown_link(record["title"], url),
        "files": [
            {
                "path": path,
                "url": f"{url}?file={quote(path, safe='')}",
                "markdown": markdown_link(path, f"{url}?file={quote(path, safe='')}"),
                "body_markdown": markdown_link(path, quote(path, safe="/")),
            }
            for path in paths
        ],
    }


def related(db: sqlite3.Connection, record: dict[str, Any]) -> list[dict[str, Any]]:
    # The document's original references remain untouched. This is only navigation.
    identities = {(ref["kind"], ref["id"]): ref for ref in json.loads(record["references_json"])}
    incoming = db.execute(
        """SELECT DISTINCT e.* FROM entries e, json_each(e.references_json) ref
        WHERE json_extract(ref.value, '$.id')=?
          AND json_extract(ref.value, '$.kind')=?
          AND e.archived_at IS NULL AND e.deleted_at IS NULL
        ORDER BY e.updated_at DESC, e.id""",
        (record["id"], record["kind"]),
    ).fetchall()
    for row in incoming:
        identities.setdefault(
            (row["kind"], row["id"]),
            {"kind": row["kind"], "id": row["id"], "version": str(row["revision"])},
        )
    identities.pop((record["kind"], record["id"]), None)
    return [related_item(db, reference) for reference in identities.values()]


def related_item(db: sqlite3.Connection, reference: dict[str, str]) -> dict[str, Any]:
    row = db.execute(
        "SELECT * FROM entries WHERE kind=? AND id=?", (reference["kind"], reference["id"])
    ).fetchone()
    if row is None:
        return {"reference": reference, "title": "关联内容已不可用", "unavailable": True}
    return {
        "reference": {"kind": row["kind"], "id": row["id"], "version": str(row["revision"])},
        "title": row["title"],
        "unavailable": bool(row["deleted_at"]),
    }
