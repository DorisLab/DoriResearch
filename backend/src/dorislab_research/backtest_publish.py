"""Export project-owned strategy/run evidence through the small host publication envelope."""

import json
import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4

from .backtest_bundle import verify_backtest, verify_files
from .backtest_request import BacktestRequest
from .bundles import digest, write_json


def package_files(output: Path, body: str) -> list[dict[str, Any]]:
    return [
        {
            "path": p.relative_to(output).as_posix(),
            "role": "body" if p.name == body else "evidence",
            "media_type": "text/markdown"
            if p.suffix == ".md"
            else mimetypes.guess_type(p.name)[0] or "application/octet-stream",
            "bytes": p.stat().st_size,
            "sha256": digest(p),
        }
        for p in sorted(output.rglob("*"))
        if p.is_file()
    ]


def copy_files(bundle: Path, output: Path, files: list[str]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for name in files:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((bundle / name).read_bytes())
        if digest(target) != digest(bundle / name):
            raise ValueError("Evidence changed during export")


def envelope(
    output: Path,
    *,
    kind: str,
    title: str,
    summary: str,
    body: str,
    nature: str,
    references: list[dict[str, str]],
    previous: Path | None,
    note: str,
) -> None:
    prior = json.loads(previous.read_bytes())["reference"] if previous else None
    if prior and (prior["kind"] != kind or not note.strip()):
        raise ValueError("Revision requires a same-kind previous receipt and a note")
    write_json(
        output / "artifact.json",
        {
            "schema": "dorislab.research.artifact.v1",
            "request_id": str(uuid4()),
            "kind": kind,
            "title": title,
            "summary": summary,
            "origin": "project",
            "data_nature": nature,
            "body": body,
            "search": body,
            "cover": "cover.png" if kind == "run" and (output / "cover.png").is_file() else None,
            "previous": prior,
            "revision_note": note,
            "references": references,
            "project_format": "dorislab.etf-momentum.v1",
            "files": package_files(output, body),
        },
    )


def export_strategy(
    bundle: Path, output: Path, previous: Path | None = None, note: str = ""
) -> Path:
    verify_backtest(bundle)
    files = verify_files(bundle)
    selected = [
        n
        for n in files
        if n.startswith("sources/") or n in {"strategy.json", "strategy.md", "runtime.json"}
    ]
    copy_files(bundle, output, selected)
    if any(digest(output / n) != files[n] for n in selected):
        raise ValueError("Strategy changed during export")
    envelope(
        output,
        kind="strategy",
        title="ETF 正动量月度轮动策略",
        summary="固定标的池的正动量筛选、月度调仓与现金仓位约束。",
        body="strategy.md",
        nature="none",
        references=[],
        previous=previous,
        note=note,
    )
    return output.resolve()


def strategy_reference(bundle: Path, package: Path, receipt_file: Path) -> dict[str, str]:
    receipt = json.loads(receipt_file.read_bytes())
    artifact = json.loads((package / "artifact.json").read_bytes())
    if (
        artifact["kind"] != "strategy"
        or receipt["reference"]["kind"] != "strategy"
        or receipt["request_id"] != artifact["request_id"]
        or receipt["index_status"] != "ready"
    ):
        raise ValueError("Strategy package and confirmed host receipt must match")
    entry = next(f for f in artifact["files"] if f["path"] == "strategy.json")
    if (
        digest(bundle / "strategy.json") != entry["sha256"]
        or digest(package / "strategy.json") != entry["sha256"]
    ):
        raise ValueError("Run strategy differs from the registered strategy version")
    reference: dict[str, str] = receipt["reference"]
    return reference


def export_backtest(
    bundle: Path, output: Path, strategy_package: Path, strategy_receipt: Path
) -> Path:
    verification = verify_backtest(bundle)
    reference = strategy_reference(bundle, strategy_package, strategy_receipt)
    request = BacktestRequest.model_validate_json((bundle / "request.json").read_bytes())
    files = verify_files(bundle)
    copy_files(bundle, output, [*files, "manifest.json"])
    verify_files(output)
    write_json(output / "replay-verification.json", verification)
    # Each calculation is a new immutable run; a retry links previous_run in request.json.
    envelope(
        output,
        kind="run",
        title=request.title,
        summary=f"{request.start}—{request.end}；"
        "日线、固定规则、无公司行动区间；成交约束为声明的研究假设。",
        body="report.md",
        nature=request.data_nature,
        references=[reference],
        previous=None,
        note="",
    )
    return output.resolve()
