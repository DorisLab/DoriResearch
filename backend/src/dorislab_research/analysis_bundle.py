"""Versioned evidence packages. Host registration is deliberately a separate capability."""

import importlib.metadata
import json
import platform
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .analysis import AnalysisRequest, AnalysisResult, calculate, report
from .bundles import digest, write_json


def snapshot_sources(destination: Path) -> None:
    sources = destination / "sources"
    sources.mkdir()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        (sources / path.name).write_bytes(path.read_bytes())
    theme = Path(__file__).with_name("chart_theme.json")
    (sources / theme.name).write_bytes(theme.read_bytes())
    for name in ("pyproject.toml", "uv.lock"):
        path = Path(__file__).parents[2] / name
        if not path.is_file():
            path = Path(__file__).parent / "locks" / name
        (sources / name).write_bytes(path.read_bytes())


def analyze(request_file: Path, destination: Path) -> Path:
    # Validate the request before creating a run; a computation failure keeps its own directory.
    request = AnalysisRequest.model_validate_json(request_file.read_bytes())
    source = Path(request.input_file)
    if not source.is_absolute():
        source = request_file.resolve().parent / source
    destination.mkdir(parents=True, exist_ok=False)
    run: dict[str, object] = {
        "schema": "dorislab.analysis.run.v1",
        "id": str(uuid4()),
        "status": "running",
        "execution_source": "project-observed",
        "created_at": datetime.now(UTC).isoformat(),
        "previous_run": request.previous_run,
        "host_registration": "not_submitted",
        "python": platform.python_version(),
        "package": importlib.metadata.version("dorislab-research"),
    }
    write_json(destination / "run.json", run)
    write_json(destination / "request.json", request.model_dump(mode="json"))
    try:
        snapshot_sources(destination)
        if source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Analysis input exceeds 20 MiB")
        data = source.read_bytes()
        if len(data) > 20 * 1024 * 1024:
            raise ValueError("Analysis input exceeds 20 MiB")
        (destination / "input.csv").write_bytes(data)
        result = calculate(data, request)
        write_json(destination / "result.json", result.model_dump(mode="json"))
        (destination / "report.md").write_text(report(request, result), encoding="utf-8")
        (destination / "execution.log").write_text("Analysis completed; domain check follows.\n")
        check_result(destination)
        write_json(
            destination / "validation.json",
            {
                "validator": "dorislab.analysis.v1",
                "status": "passed",
                "checks": ["input-schema", "finite-values", "scope", "descriptive-statistics"],
            },
        )
        run.update(status="succeeded", finished_at=datetime.now(UTC).isoformat())
    except Exception as error:
        run.update(
            status="failed",
            finished_at=datetime.now(UTC).isoformat(),
            error=f"{type(error).__name__}: {error}",
        )
        (destination / "execution.log").write_text(str(run["error"]), encoding="utf-8")
        raise
    finally:
        write_json(destination / "run.json", run)
        files = {
            p.relative_to(destination).as_posix(): digest(p)
            for p in sorted(destination.rglob("*"))
            if p.is_file() and p.name != "manifest.json"
        }
        write_json(
            destination / "manifest.json", {"schema": "dorislab.analysis.files.v1", "files": files}
        )
    return destination.resolve()


def check_result(root: Path) -> AnalysisResult:
    request = AnalysisRequest.model_validate_json((root / "request.json").read_bytes())
    result = AnalysisResult.model_validate_json((root / "result.json").read_bytes())
    expected = calculate((root / "input.csv").read_bytes(), request)
    if result != expected:
        raise ValueError("Result does not match the frozen input and method")
    if (root / "report.md").read_text(encoding="utf-8") != report(request, result):
        raise ValueError("Generated report does not match the result")
    return result


def verify_analysis(root: Path) -> AnalysisResult:
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest.get("schema") != "dorislab.analysis.files.v1":
        raise ValueError("Unsupported analysis manifest")
    files = manifest["files"]
    required = {
        "run.json",
        "request.json",
        "input.csv",
        "result.json",
        "report.md",
        "validation.json",
        "execution.log",
        "sources/analysis.py",
        "sources/uv.lock",
    }
    if not required <= files.keys():
        raise ValueError("Missing required analysis evidence")
    for name, expected in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise ValueError("Unsafe analysis path")
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("Missing or escaped analysis file")
        if any(
            p.is_symlink() or p.is_junction() for p in (path, *path.parents) if p != root.parent
        ):
            raise ValueError("Analysis package cannot contain links")
        if digest(path) != expected:
            raise ValueError(f"Analysis integrity check failed: {name}")
    run = json.loads((root / "run.json").read_bytes())
    if run.get("status") != "succeeded":
        raise ValueError("Analysis execution is not successful")
    validation = json.loads((root / "validation.json").read_bytes())
    if (
        validation.get("status") != "passed"
        or validation.get("validator") != "dorislab.analysis.v1"
    ):
        raise ValueError("Analysis domain check has not passed")
    return check_result(root)
