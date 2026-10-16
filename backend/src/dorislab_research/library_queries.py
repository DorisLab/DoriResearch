import json
import math
import shutil
import time
from typing import Any

from .database import connect, writable
from .library import Library


def summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference": {"id": row["id"], "kind": row["kind"], "version": str(row["revision"])},
        "title": row["title"],
        "summary": row["summary"],
        "snippet": row["summary"],
        "origin": row["origin"],
        "data_nature": row["data_nature"],
        "registered_at": row["updated_at"],
        "references": json.loads(row["references_json"]),
        "cover": json.loads(row["config_json"]).get("cover"),
    }


def listing(library: Library, query: str = "", kind: str = "") -> list[dict[str, Any]]:
    # Substring matching also works for Chinese without a language-specific FTS tokenizer.
    with connect(library.root) as db:
        rows = db.execute(
            """SELECT * FROM entries WHERE deleted_at IS NULL
            AND archived_at IS NULL AND (?='' OR kind=?)
            AND instr(lower(title||' '||summary||' '||body),lower(?))>0
            ORDER BY updated_at DESC,id""",
            (kind, kind, query),
        ).fetchall()
    return [summary(dict(row)) for row in rows]


def page(library: Library, request: dict[str, Any]) -> dict[str, Any]:
    items = listing(library, request.get("query", ""), request.get("kind", ""))
    order = request.get("sort", "newest")
    if order == "oldest":
        items.reverse()
    elif order == "title":
        items.sort(key=lambda item: item["title"])
    elif order != "newest":
        raise ValueError("排序方式无效")
    number = max(1, min(int(request.get("page", 1)), math.ceil(len(items) / 20)))
    return {"items": items[(number - 1) * 20 : number * 20], "total": len(items), "page": number}


def status(library: Library, reference: dict[str, str]) -> dict[str, Any]:
    with connect(library.root) as db:
        row = db.execute(
            "SELECT * FROM entries WHERE id=? AND kind=?",
            (
                reference["id"],
                reference["kind"],
            ),
        ).fetchone()
        revision = db.execute(
            "SELECT content FROM revisions WHERE id=? AND revision=?",
            (reference["id"], int(reference["version"])),
        ).fetchone()
    if not row:
        raise ValueError("内容不存在")
    if not revision:
        raise ValueError("内容版本不存在")
    saved = json.loads(revision[0])
    return {
        "reference": reference,
        **{
            key: row[key]
            for key in (
                "title",
                "summary",
                "archived_at",
                "deleted_at",
            )
        },
        "title": saved["title"],
        "summary": saved["summary"],
    }


def archive(library: Library, reference: dict[str, str], archived: bool) -> None:
    current = status(library, reference)
    if current["deleted_at"]:
        raise ValueError("内容已删除，无法恢复")
    with connect(library.root) as db:
        db.execute("BEGIN IMMEDIATE")
        writable(library.root)
        db.execute(
            "UPDATE entries SET archived_at=? WHERE id=?",
            (
                (current["archived_at"] or int(time.time() * 1000)) if archived else None,
                reference["id"],
            ),
        )


def archives(library: Library) -> list[dict[str, Any]]:
    with connect(library.root) as db:
        rows = db.execute("""SELECT * FROM entries WHERE archived_at IS NOT NULL
            AND deleted_at IS NULL ORDER BY archived_at DESC""").fetchall()
    return [
        {
            "id": row["id"],
            "workspace_id": "",
            "kind": row["kind"],
            "reference": summary(dict(row))["reference"],
            "title": row["title"],
            "summary": row["summary"],
            "archived_at": row["archived_at"],
            "deleting": False,
            "error": None,
        }
        for row in rows
    ]


def delete(library: Library, ids: list[str]) -> None:
    with connect(library.root) as db:
        db.execute("BEGIN IMMEDIATE")
        writable(library.root)
        for identity in ids:
            row = db.execute("SELECT archived_at FROM entries WHERE id=?", (identity,)).fetchone()
            if not row or row[0] is None:
                raise ValueError("只能删除已归档内容")
        for identity in ids:
            # Keep title/summary as a tombstone; related content is never cascaded.
            db.execute(
                "UPDATE entries SET deleted_at=?,body='',config_json='{}' WHERE id=?",
                (
                    int(time.time() * 1000),
                    identity,
                ),
            )
            db.execute("DELETE FROM search WHERE id=?", (identity,))
    cleanup_deleted(library)


def cleanup_deleted(library: Library) -> None:
    with connect(library.root) as db:
        rows = db.execute("""SELECT r.id,r.revision,r.content FROM revisions r JOIN entries e
            ON e.id=r.id WHERE e.deleted_at IS NOT NULL""").fetchall()
        for row in rows:
            content = json.loads(row["content"])
            if not content.get("directory"):
                continue
            directory = library.root / "files" / content["directory"]
            if directory.is_dir():
                shutil.rmtree(directory)
            db.execute(
                "UPDATE revisions SET content=? WHERE id=? AND revision=?",
                (
                    json.dumps({key: content[key] for key in ("title", "summary")}),
                    row["id"],
                    row["revision"],
                ),
            )


def expire(library: Library) -> None:
    cutoff = int(time.time() * 1000) - 7 * 86400 * 1000
    delete(library, [item["id"] for item in archives(library) if item["archived_at"] <= cutoff])
