"""One save entry point; retry keeps the original package identity and immutable bytes."""

import json
import tempfile
from pathlib import Path

from .bundles import digest
from .publish import publish
from .study_export import StudyRequest, export_study, safe_file


def save_study(
    request_path: Path,
    output: Path,
    previous: Path | None = None,
    note: str = "",
    project: Path | None = None,
) -> dict[str, object]:
    request = StudyRequest.model_validate_json(request_path.read_bytes())
    if not request.execution:
        raise ValueError("Saving a resumable study requires execution materials; see study-schema")
    if output.exists():
        verify_retry(request_path, output, previous, note)
    else:
        export_study(request_path, output, previous, note)
    return publish(output, project) if project else publish(output)


def verify_retry(request_path: Path, output: Path, previous: Path | None, note: str) -> None:
    package = json.loads((output / "artifact.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix=".retry-", dir=output.parent) as directory:
        expected = export_study(request_path, Path(directory) / "package", previous, note)
        manifest = json.loads((expected / "artifact.json").read_bytes())
        manifest["request_id"] = package["request_id"]
        if manifest != package:
            raise ValueError("Study request or evidence changed; use a new output directory")
    for file in package["files"]:
        path = safe_file(output, file["path"])
        if path.stat().st_size != file["bytes"] or digest(path) != file["sha256"]:
            raise ValueError("Study evidence changed; use a new output directory for a new version")
