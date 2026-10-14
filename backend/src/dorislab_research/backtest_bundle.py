"""Immutable local runs. Replay verifies facts; host registration remains a separate step."""

import importlib.metadata
import json
import platform
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from doribt import Backtest, BarExecution, Costs, FixedBps, RunConfig
from doribt.reporting.benchmark import Benchmark

from .analysis_bundle import snapshot_sources
from .backtest_data import freeze_inputs, market_from
from .backtest_report import report, strategy_report
from .backtest_request import BacktestRequest, MomentumParameters
from .backtest_result import normalize
from .bundles import digest, write_json
from .momentum import MonthlyMomentum


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("doribt", "numpy", "pydantic", "pyarrow", "matplotlib")
        },
    }


def strategy_definition(root: Path) -> dict[str, Any]:
    return {
        "schema": "dorislab.strategy.v1",
        "profile": "dorislab.etf-momentum.v1",
        "entrypoint": "dorislab_research.momentum.MonthlyMomentum",
        "code_sha256": digest(root / "sources/momentum.py"),
        "parameter_schema": MomentumParameters.model_json_schema(),
        "default_parameters": MomentumParameters().model_dump(mode="json"),
        "request_schema": BacktestRequest.model_json_schema(),
        "engine": f"doribt=={importlib.metadata.version('doribt')}",
    }


def execute(inputs: dict[str, Any], request: BacktestRequest, root: Path) -> dict[str, Any]:
    from .charting import save_figure

    assumptions = request.assumptions
    config = RunConfig(
        initial_cash=request.initial_cash,
        costs=Costs(
            commission=assumptions.commission, minimum_commission=assumptions.minimum_commission
        ),
        execution=BarExecution(
            slippage=FixedBps(assumptions.slippage_bps), participation=assumptions.max_participation
        ),
    )
    result = Backtest(market_from(inputs, request), config=config).run(MonthlyMomentum(request))
    result.export(root / "engine", daily=True, risk_free_rate=request.risk_free_rate)
    normalized = normalize(result, request, inputs)
    benchmark = None
    if normalized["benchmark"]["definition"] == "cash_zero":
        benchmark = Benchmark(
            sessions=result.sessions,
            prices=[1.0] * len(result.sessions),
            name="现金基准（零利息）",
            source="本次运行声明的现金基准",
        )
    save_figure(result.plot(benchmark=benchmark), root / "cover.png", dpi=120)
    write_json(root / "result.json", normalized)
    write_json(
        root / "charts.json",
        {
            "schema": "dorislab.backtest.chart.v1",
            "account": [
                {key: row[key] for key in ("date", "nav", "drawdown", "exposure")}
                for row in normalized["account"]
            ],
            "monthly": normalized["monthly"],
            "benchmark": normalized["benchmark"],
        },
    )
    (root / "report.md").write_text(report(request, normalized), encoding="utf-8")
    return normalized


def overview(
    run: dict[str, Any], request: BacktestRequest, result: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "dorislab.backtest.overview.v1",
        "status": run["status"],
        "created_at": run["created_at"],
        "start": str(request.start),
        "end": str(request.end),
        "metrics": result["metrics"],
    }


def backtest(catalog: Path, request_file: Path, output: Path) -> Path:
    request = BacktestRequest.model_validate_json(request_file.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    run: dict[str, Any] = {
        "schema": "dorislab.backtest.run.v1",
        "id": str(uuid4()),
        "status": "running",
        "created_at": datetime.now(UTC).isoformat(),
        "execution_source": "project-observed",
        "previous_run": request.previous_run,
        "host_registration": "not_submitted",
    }
    write_json(output / "run.json", run)
    write_json(output / "request.json", request.model_dump(mode="json"))
    try:
        snapshot_sources(output)
        write_json(output / "runtime.json", environment())
        definition = strategy_definition(output)
        write_json(output / "strategy.json", definition)
        (output / "strategy.md").write_text(strategy_report(definition), encoding="utf-8")
        inputs = freeze_inputs(catalog, request, output)
        normalized = execute(inputs, request, output)
        write_json(
            output / "validation.json",
            {
                "status": "passed",
                "validator": request.profile,
                "checks": [
                    "source-object-hashes",
                    "calendar-coverage",
                    "no-actions",
                    "bar-coverage",
                    "account-identity",
                    "cash-and-position-ledger-replay",
                    "order-fill-links",
                ],
                "independent_engine_rerun": "not_yet_performed",
            },
        )
        run.update(status="succeeded", finished_at=datetime.now(UTC).isoformat())
        write_json(output / "overview.json", overview(run, request, normalized))
        (output / "execution.log").write_text("DoriBT completed; account and ledger reconciled.\n")
    except Exception as error:
        run.update(
            status="failed",
            finished_at=datetime.now(UTC).isoformat(),
            error=f"{type(error).__name__}: {error}",
        )
        (output / "execution.log").write_text(run["error"], encoding="utf-8")
        raise
    finally:
        write_json(output / "run.json", run)
        write_json(
            output / "manifest.json",
            {
                "schema": "dorislab.backtest.files.v1",
                "files": {
                    p.relative_to(output).as_posix(): digest(p)
                    for p in sorted(output.rglob("*"))
                    if p.is_file() and p != output / "manifest.json"
                },
            },
        )
    return output.resolve()


def verify_files(root: Path) -> dict[str, str]:
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest.get("schema") != "dorislab.backtest.files.v1":
        raise ValueError("Unsupported backtest manifest")
    files: dict[str, str] = manifest["files"]
    required = {
        "request.json",
        "input.json",
        "run.json",
        "result.json",
        "runtime.json",
        "report.md",
        "strategy.json",
        "strategy.md",
        "validation.json",
        "execution.log",
        "bars-provenance.json",
        "calendar-provenance.json",
        "actions-provenance.json",
        "engine/ledger.json",
        "engine/account.csv",
        "engine/positions.csv",
        "sources/uv.lock",
    }
    if not required <= files.keys():
        raise ValueError("Missing required backtest evidence")
    for name, expected in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise ValueError("Unsafe backtest evidence path")
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("Missing or escaped backtest evidence")
        if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
            raise ValueError("Backtest evidence cannot contain links")
        if digest(path) != expected:
            raise ValueError(f"Backtest integrity check failed: {name}")
    if json.loads((root / "run.json").read_bytes())["status"] != "succeeded":
        raise ValueError("Backtest execution did not succeed")
    return files


def verify_backtest(root: Path) -> dict[str, Any]:
    files = verify_files(root)
    if json.loads((root / "runtime.json").read_bytes()) != environment():
        raise ValueError("Replay requires the archived Python and dependency versions")
    for name, expected in files.items():
        if name.startswith("sources/") and name.endswith(".py"):
            source = Path(__file__).parent / Path(name).name
            if not source.is_file() or digest(source) != expected:
                raise ValueError("Replay requires archived source; current project has changed")
    request = BacktestRequest.model_validate_json((root / "request.json").read_bytes())
    inputs = json.loads((root / "input.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix="dorislab-replay-") as temporary:
        replay = Path(temporary)
        execute(inputs, request, replay)
        compared = [
            name
            for name in files
            if name.startswith("engine/") or name in {"result.json", "charts.json", "report.md"}
        ]
        for name in compared:
            if digest(replay / name) != files[name]:
                raise ValueError(f"Independent replay differs: {name}")
    if "overview.json" in files:
        expected_overview = overview(
            json.loads((root / "run.json").read_bytes()),
            request,
            json.loads((root / "result.json").read_bytes()),
        )
        if json.loads((root / "overview.json").read_bytes()) != expected_overview:
            raise ValueError("Run overview does not match frozen evidence")
    if json.loads((root / "strategy.json").read_bytes()) != strategy_definition(root):
        raise ValueError("Strategy definition does not match frozen sources")
    return {
        "status": "passed",
        "integrity": "passed",
        "independent_engine_rerun": "exact",
        "compared": compared,
        "strategy_validity": "not_established",
    }
