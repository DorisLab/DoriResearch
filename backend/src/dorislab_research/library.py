"""Small ordinary Python API for editable content; no export or registration phase."""

import json
import mimetypes
import secrets
import shutil
import sqlite3
import string
import time
import uuid
from pathlib import Path
from typing import Any

from .database import connect, data_root, writable


class ConflictError(ValueError):
    """The author edited an old revision. Re-read and reconcile before retrying."""


def allocate(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    while True:
        name = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        path = root / name
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue


def local_file(root: Path, name: str) -> Path:
    path = Path(name)
    if (
        path.is_absolute()
        or not path.parts
        or ":" in name
        or any(p in ("..", ".") for p in path.parts)
    ):
        raise ValueError("文件必须使用内容目录内的相对路径")
    target = root.joinpath(path)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("文件链接指向内容目录之外")
    return target


class Library:
    def __init__(self, root: Path | None = None):
        self.root = data_root(root)

    def save(
        self,
        *,
        kind: str,
        title: str,
        body: str,
        summary: str = "",
        files: dict[str, Path] | None = None,
        references: list[dict[str, str]] | None = None,
        config: dict[str, Any] | None = None,
        id: str | None = None,
        expected_revision: int | None = None,
        origin: str = "project",
        data_nature: str = "none",
    ) -> dict[str, str]:
        if kind not in ("study", "strategy", "run") or not title.strip():
            raise ValueError("请提供研究、策略或策略结果，以及标题")
        with connect(self.root) as db:
            db.execute("BEGIN IMMEDIATE")
            writable(self.root)
            old = db.execute("SELECT * FROM entries WHERE id=?", (id,)).fetchone()
            if (old and old["deleted_at"]) or (not old and expected_revision is not None):
                raise ValueError("内容已删除或不存在")
            if old and old["kind"] != kind:
                raise ValueError("已有内容不能改换分类")
            if old and expected_revision != old["revision"]:
                raise ConflictError("内容已被修改，请重新读取后整合")
            revision = old["revision"] + 1 if old else 1
            folder = allocate(self.root / "files")
            identity = id or str(uuid.uuid4())
            now = int(time.time() * 1000)
            try:
                (folder / "report.md").write_text(body, encoding="utf-8")
                for name, source in (files or {}).items():
                    if name == "report.md":
                        raise ValueError("report.md 由正文参数保存")
                    destination = local_file(folder, name)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
                save_entry(
                    db,
                    identity,
                    kind,
                    revision,
                    title,
                    summary,
                    body,
                    folder.name,
                    origin,
                    data_nature,
                    references or [],
                    config or {},
                    old["created_at"] if old else now,
                    now,
                )
                record = dict(
                    db.execute("SELECT * FROM entries WHERE id=?", (identity,)).fetchone()
                )
                db.execute(
                    "INSERT INTO revisions VALUES (?,?,?)",
                    (
                        identity,
                        revision,
                        json.dumps(record, ensure_ascii=False),
                    ),
                )
                db.execute("DELETE FROM search WHERE id=?", (identity,))
                db.execute("INSERT INTO search VALUES (?,?,?,?)", (identity, title, summary, body))
                db.commit()
            except BaseException:
                shutil.rmtree(folder)
                raise
        return {"kind": kind, "id": identity, "version": str(revision)}

    def record(self, reference: dict[str, str]) -> dict[str, Any]:
        with connect(self.root) as db:
            live = db.execute("SELECT * FROM entries WHERE id=?", (reference["id"],)).fetchone()
            if not live or live["kind"] != reference["kind"]:
                raise ValueError("内容不存在")
            if live["deleted_at"]:
                raise ValueError(f"该内容已被删除\n{live['summary']}")
            version = reference.get("version", str(live["revision"]))
            row = db.execute(
                "SELECT content FROM revisions WHERE id=? AND revision=?",
                (
                    reference["id"],
                    int(version),
                ),
            ).fetchone()
            if not row:
                raise ValueError("内容版本不存在")
            return dict(json.loads(row[0]))

    def file(self, reference: dict[str, str], path: str) -> Path:
        record = self.record(reference)
        return local_file(self.root / "files" / record["directory"], path)

    def content(self, reference: dict[str, str]) -> dict[str, Any]:
        from .library_queries import summary

        record = self.record(reference)
        directory = self.root / "files" / record["directory"]
        files = [
            {
                "path": p.relative_to(directory).as_posix(),
                "bytes": p.stat().st_size,
                "media_type": mimetypes.guess_type(p)[0] or "application/octet-stream",
                "role": "attachment",
                "sha256": "",
            }
            for p in sorted(directory.rglob("*"))
            if p.is_file()
        ]
        return {
            "item": {**summary(record), "files": files},
            "body": record["body"],
            "files": files,
            "references": json.loads(record["references_json"]),
            "revision_note": "",
            "config": json.loads(record["config_json"]),
        }


def save_entry(
    db: sqlite3.Connection,
    identity: str,
    kind: str,
    revision: int,
    title: str,
    summary: str,
    body: str,
    directory: str,
    origin: str,
    data_nature: str,
    references: list[dict[str, str]],
    config: dict[str, Any],
    created_at: int,
    now: int,
) -> None:
    values = (
        identity,
        kind,
        revision,
        title,
        summary,
        body,
        directory,
        origin,
        data_nature,
        json.dumps(references),
        json.dumps(config),
        created_at,
        now,
    )
    db.execute(
        """INSERT INTO entries
        (id,kind,revision,title,summary,body,directory,origin,data_nature,
         references_json,config_json,created_at,updated_at)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,title=excluded.title,
        summary=excluded.summary,body=excluded.body,directory=excluded.directory,
        references_json=excluded.references_json,config_json=excluded.config_json,
        updated_at=excluded.updated_at,data_nature=excluded.data_nature""",
        values,
    )
