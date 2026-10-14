"""Package an arbitrary study without prescribing its calculations or metrics."""

from __future__ import annotations

import json
import mimetypes
import tempfile
from pathlib import Path, PurePosixPath
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .bundles import digest, write_json
from .execution_materials import ExecutionMaterials


class StudyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=250)
    summary: str = Field(min_length=1, max_length=4000)
    data_nature: Literal["real", "synthetic", "mixed", "none"]
    body: str = "report.md"
    files: list[str] = Field(min_length=1, max_length=255)
    cover: str | None = None
    reproduction: str | None = Field(default=None, max_length=8000)
    execution: ExecutionMaterials | None = None


def safe_file(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if (
        not parts
        or name != "/".join(parts)
        or any(c in name for c in "\\:%?#")
        or any(ord(c) < 32 for c in name)
        or any(p in {".", ".."} or p.endswith((".", " ")) for p in parts)
        or PurePosixPath(name).is_absolute()
    ):
        raise ValueError(f"Invalid relative study file: {name}")
    path = root
    for part in parts:
        path /= part
        if path.is_symlink() or path.is_junction():
            raise ValueError("Study files cannot be links")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Study file is missing or outside the study: {name}")
    return path


def evidence(request: StudyRequest, root: Path) -> dict[str, bytes]:
    if request.execution:
        request.execution.validate_files(request.files)
    names = [name.casefold() for name in request.files]
    if (
        len(set(names)) != len(names)
        or {"artifact.json", "study.json"} & set(names)
        or any(name.split("/")[0] == "_dorislab" for name in names)
    ):
        raise ValueError("Duplicate or reserved study file name")
    if request.body not in request.files or (request.cover and request.cover not in request.files):
        raise ValueError("Body and cover must be included in files")
    values = {}
    total = 0
    for name in request.files:
        path = safe_file(root, name)
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Study file exceeds 32 MiB")
        with path.open("rb") as stream:
            value = stream.read(32 * 1024 * 1024 + 1)
        total += len(value)
        if len(value) > 32 * 1024 * 1024 or total > 64 * 1024 * 1024 - 65536:
            raise ValueError("Study evidence exceeds host limits")
        values[name] = value
    body = values[request.body]
    if len(body) > 1024 * 1024 or not body.decode("utf-8-sig").strip():
        raise ValueError("Study body must be nonempty UTF-8 text within 1 MiB")
    if request.cover:
        mime = media_type(request.cover)
        if (
            mime not in {"image/png", "image/jpeg", "image/webp"}
            or len(values[request.cover]) > 1024 * 1024
        ):
            raise ValueError("Cover must be PNG/JPEG/WebP within 1 MiB")
    return values


def media_type(name: str) -> str:
    return (
        "text/markdown"
        if name.endswith((".md", ".markdown"))
        else (mimetypes.guess_type(name)[0] or "application/octet-stream")
    )


def export_study(
    request_path: Path, output: Path, previous: Path | None = None, note: str = ""
) -> Path:
    request = StudyRequest.model_validate_json(request_path.read_bytes())
    values = evidence(request, request_path.parent)
    prior = json.loads(previous.read_bytes())["reference"] if previous else None
    if prior and (prior["kind"] != "study" or not note.strip()):
        raise ValueError("A study revision requires a study receipt and --note")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".study-", dir=output.parent) as directory:
        staging = Path(directory) / "package"
        staging.mkdir()
        for name, value in values.items():
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(value)
        write_json(staging / "study.json", request.model_dump())
        files = []
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                name = path.relative_to(staging).as_posix()
                files.append(
                    {
                        "path": name,
                        "role": "body" if name == request.body else "evidence",
                        "media_type": "text/markdown" if name == request.body else media_type(name),
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                    }
                )
        write_json(
            staging / "artifact.json",
            {
                "schema": "dorislab.research.artifact.v1",
                "request_id": str(uuid4()),
                "kind": "study",
                "title": request.title,
                "summary": request.summary,
                "origin": "project",
                "data_nature": request.data_nature,
                "body": request.body,
                "search": request.body,
                "cover": request.cover,
                "previous": prior,
                "revision_note": note,
                "references": [],
                "project_format": "dorislab.study.v1",
                "files": files,
                **({"execution": request.execution.model_dump()} if request.execution else {}),
            },
        )
        staging.rename(output)
    return output.resolve()
