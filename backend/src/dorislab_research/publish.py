"""Project export adapter and a thin, run-scoped host client. Never writes host state."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
from pathlib import Path
from uuid import uuid4

from .analysis import AnalysisRequest
from .analysis_bundle import verify_analysis
from .bundles import digest, write_json
from .study_export import StudyRequest, export_study


def export_analysis(
    bundle: Path, output: Path, previous: Path | None = None, note: str = ""
) -> Path:
    result = verify_analysis(bundle)
    request = AnalysisRequest.model_validate_json((bundle / "request.json").read_bytes())
    prior = json.loads(previous.read_bytes())["reference"] if previous else None
    if prior and not note.strip():
        raise ValueError("A revision requires --note and a previous host receipt")
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    for name in [*manifest["files"], "manifest.json"]:
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((bundle / name).read_bytes())
    # Validate the copied evidence as well, so an export never legitimizes changed inputs.
    verify_analysis(output)
    files = []
    for path in sorted(output.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(output).as_posix()
        media_type = "text/markdown" if path.suffix == ".md" else mimetypes.guess_type(name)[0]
        files.append(
            {
                "path": name,
                "role": "body" if name == "report.md" else "evidence",
                "media_type": media_type or "application/octet-stream",
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    write_json(
        output / "artifact.json",
        {
            "schema": "dorislab.research.artifact.v1",
            "request_id": str(uuid4()),
            "kind": "study",
            "title": request.title,
            "summary": f"{request.question} 范围 {result.start}—{result.end}，"
            f"{result.observations} 个观察值，变化 {result.change:g} {result.unit}。",
            "origin": "project",
            "data_nature": request.data_nature,
            "body": "report.md",
            "search": "report.md",
            "cover": None,
            "previous": prior,
            "revision_note": note,
            "references": [],
            "project_format": "dorislab.analysis.v1",
            "files": files,
        },
    )
    return output.resolve()


def host_request(command: dict[str, object]) -> dict[str, object]:
    endpoint = os.environ.get("DORISLAB_RESEARCH_ENDPOINT", "")
    capability = os.environ.get("DORISLAB_RESEARCH_CAPABILITY", "")
    host, _, port = endpoint.partition(":")
    if host != "127.0.0.1" or not port.isdecimal() or len(capability) != 64:
        raise ValueError("Host registration is unavailable outside a Dorislab Agent run")
    payload = {"capability": capability, **command}
    try:
        with socket.create_connection((host, int(port)), timeout=30) as connection:
            connection.sendall(json.dumps(payload).encode() + b"\n")
            with connection.makefile("rb") as stream:
                response = stream.readline(256 * 1024 + 1)
    except OSError as error:
        raise ValueError(
            "Host response not confirmed; saved packages can be retried with the same identity"
        ) from error
    if not response.endswith(b"\n") or len(response) > 256 * 1024:
        raise ValueError("Host response not confirmed; retry with the same saved package")
    reply: dict[str, object] = json.loads(response)
    if reply.get("status") != "ready":
        raise ValueError(reply.get("message", "Host rejected the request"))
    return reply


def publish(package: Path, project: Path | None = None) -> dict[str, object]:
    artifact = {"package": str(package.resolve())}
    if project is not None:
        artifact["project"] = str(project.resolve())
    reply = host_request({"artifact": artifact})
    receipt = reply["receipt"]
    if not isinstance(receipt, dict):
        raise ValueError("Invalid host receipt")
    # The receipt is adapter state, outside the immutable exported package.
    receipt_path = package.with_name(package.name + ".receipt.json")
    temporary = receipt_path.with_suffix(".tmp")
    write_json(temporary, receipt)
    temporary.replace(receipt_path)
    return receipt


def add_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    sub.add_parser("prepare-project", help="Create or resume this conversation's isolated project")
    study = sub.add_parser(
        "export-study", help="Package a research report, code and evidence for the host"
    )
    study.add_argument("--request", required=True, type=Path)
    study.add_argument("--output", required=True, type=Path)
    study.add_argument("--previous", type=Path)
    study.add_argument("--note", default="")
    sub.add_parser("study-schema", help="Print the generic study export request JSON Schema")
    export = sub.add_parser("export-analysis", help="Verify and export an analysis for the host")
    export.add_argument("--bundle", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--previous", type=Path, help="Previous host receipt, for a new revision")
    export.add_argument("--note", default="")
    submit = sub.add_parser("publish", help="Register an exported package in the current account")
    submit.add_argument("--package", required=True, type=Path)
    submit.add_argument(
        "--project", type=Path, help="Prepared source directory when continuing a saved version"
    )
    save = sub.add_parser("save-study", help="Freeze resumable materials and register a study")
    save.add_argument("--request", required=True, type=Path)
    save.add_argument("--output", required=True, type=Path)
    save.add_argument("--previous", type=Path)
    save.add_argument("--note", default="")
    save.add_argument(
        "--project", type=Path, help="Prepared source directory when continuing a saved version"
    )
    prepare = sub.add_parser("prepare-publication", help="Copy exact saved materials for new work")
    prepare.add_argument("--receipt", required=True, type=Path)


def run(arguments: argparse.Namespace) -> None:
    if arguments.command == "prepare-project":
        print(json.dumps(host_request({"prepare_project": {}})["prepared"], indent=2))
    elif arguments.command == "save-study":
        from .delivery import save_study

        print(
            json.dumps(
                save_study(
                    arguments.request,
                    arguments.output,
                    arguments.previous,
                    arguments.note,
                    arguments.project,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif arguments.command == "prepare-publication":
        reference = json.loads(arguments.receipt.read_bytes())["reference"]
        print(
            json.dumps(
                host_request({"prepare_publication": reference})["prepared"],
                ensure_ascii=False,
                indent=2,
            )
        )
    elif arguments.command == "study-schema":
        print(json.dumps(StudyRequest.model_json_schema(), ensure_ascii=False, indent=2))
    elif arguments.command == "export-study":
        print(export_study(arguments.request, arguments.output, arguments.previous, arguments.note))
    elif arguments.command == "export-analysis":
        print(
            export_analysis(arguments.bundle, arguments.output, arguments.previous, arguments.note)
        )
    else:
        print(
            json.dumps(publish(arguments.package, arguments.project), ensure_ascii=False, indent=2)
        )
