"""Real DoriBT execution against synthetic inputs: time, costs, evidence, and refusal paths."""

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from backtest_fixture import fixture, inputs, request

from dorislab_research.backtest_bundle import backtest, verify_backtest
from dorislab_research.backtest_publish import export_backtest, export_strategy
from dorislab_research.bundles import digest, write_json


def test_actual_engine_replay_export_lineage_and_costs(tmp_path: Path) -> None:
    catalog, parameters = fixture(tmp_path / "inputs")
    bundle = backtest(catalog, parameters, tmp_path / "run")
    verification = verify_backtest(bundle)
    assert verification["independent_engine_rerun"] == "exact"
    assert "engine/ledger.json" in verification["compared"]
    result = json.loads((bundle / "result.json").read_bytes())
    overview = json.loads((bundle / "overview.json").read_bytes())
    assert overview["schema"] == "dorislab.backtest.overview.v1"
    assert overview["status"] == "succeeded"
    assert overview["start"] == "2025-01-10"
    assert overview["metrics"] == result["metrics"]
    assert overview["created_at"] == json.loads((bundle / "run.json").read_bytes())["created_at"]
    engine_version = version("doribt")
    definition = json.loads((bundle / "strategy.json").read_bytes())
    runtime = json.loads((bundle / "runtime.json").read_bytes())
    assert definition["engine"] == f"doribt=={engine_version}"
    assert runtime["packages"]["doribt"] == engine_version
    charts = json.loads((bundle / "charts.json").read_bytes())
    assert "charts.json" in verification["compared"]
    assert charts["schema"] == "dorislab.backtest.chart.v1"
    assert charts["account"] == [
        {key: row[key] for key in ("date", "nav", "drawdown", "exposure")}
        for row in result["account"]
    ]
    assert charts["monthly"] == result["monthly"]
    assert charts["benchmark"] == result["benchmark"]
    metrics = {m["metric_id"]: m for m in result["metrics"]}
    assert result["account"][0]["date"] == "2025-01-10"
    assert result["account"][0]["equity"] == 100000
    fills = json.loads((bundle / "engine/ledger.json").read_bytes())["fills"]
    assert fills and fills[0]["session"] == "2025-01-13"
    assert sum(f["commission_units"] for f in fills) / 10000 == metrics["fees"]["value"]
    assert metrics["max_drawdown"]["value"] > 0
    assert metrics["worst_complete_month"]["parameters"]["samples"] == 2
    assert metrics["benchmark_return"]["status"] == "not_applicable"
    strategy = export_strategy(bundle, tmp_path / "strategy")
    artifact = json.loads((strategy / "artifact.json").read_bytes())
    assert artifact["cover"] is None
    receipt = tmp_path / "strategy.receipt.json"
    reference = {"kind": "strategy", "id": str(uuid4()), "version": "1"}
    write_json(
        receipt,
        {"reference": reference, "request_id": artifact["request_id"], "index_status": "ready"},
    )
    exported = export_backtest(bundle, tmp_path / "export", strategy, receipt)
    package = json.loads((exported / "artifact.json").read_bytes())
    assert json.loads((exported / "overview.json").read_bytes()) == overview
    assert any(file["path"] == "overview.json" for file in package["files"])
    assert package["cover"] == "cover.png"
    assert (exported / "cover.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert (exported / "cover.png").stat().st_size < 1024 * 1024
    assert any(file["path"] == "cover.png" for file in package["files"])
    assert json.loads((exported / "artifact.json").read_bytes())["references"] == [reference]
    assert json.loads((exported / "artifact.json").read_bytes())["data_nature"] == "synthetic"
    write_json(
        receipt, {"reference": reference, "request_id": str(uuid4()), "index_status": "ready"}
    )
    with pytest.raises(ValueError, match="receipt must match"):
        export_backtest(bundle, tmp_path / "wrong", strategy, receipt)
    with pytest.raises(FileExistsError):
        backtest(catalog, parameters, bundle)


def test_zero_trades_keep_account_and_typed_empty_ledgers(tmp_path: Path) -> None:
    values = request()
    values["parameters"]["max_exposure"] = "0"
    catalog, parameters = fixture(tmp_path / "input", parameters=values)
    root = backtest(catalog, parameters, tmp_path / "zero")
    result = json.loads((root / "result.json").read_bytes())
    assert result["fill_count"] == 0 and result["order_count"] == 0
    assert all(r["equity"] == 100000 for r in result["account"])
    assert (root / "engine/fills.csv").read_text().startswith("fill_id,order_id")
    metrics = {m["metric_id"]: m for m in result["metrics"]}
    assert metrics["sharpe"]["value"] is None
    assert metrics["sortino"]["value"] is None
    assert metrics["annual_volatility"]["value"] == 0
    assert metrics["max_drawdown"]["value"] == 0


@pytest.mark.parametrize(
    "fault,message",
    [
        ("action", "Corporate actions"),
        ("missing", "Missing/extra"),
        ("calendar", "calendar is missing"),
        ("preclose", "Previous close mismatch"),
        ("suspension", "Unconfirmed"),
        ("null", "Missing/non-numeric"),
    ],
)
def test_invalid_market_facts_keep_failed_run(tmp_path: Path, fault: str, message: str) -> None:
    data = inputs()
    if fault == "action":
        data["actions"] = [
            {
                "symbol": "ETF_A",
                "trade_date": "2025-02-03",
                **dict.fromkeys(
                    (
                        "interest",
                        "stock_bonus",
                        "stock_gift",
                        "allot_num",
                        "allot_price",
                        "gugai",
                        "dr",
                    ),
                    1,
                ),
            }
        ]
    elif fault == "missing":
        data["bars"].pop(10)
    elif fault == "calendar":
        data["calendar"].pop(5)
    elif fault == "preclose":
        data["bars"][10]["pre_close"] += 0.01
    elif fault == "suspension":
        data["bars"][10]["suspend_flag"] = None
    else:
        data["bars"][10]["close"] = None
    catalog, parameters = fixture(tmp_path / "input", data)
    with pytest.raises(ValueError):
        backtest(catalog, parameters, tmp_path / "failed")
    run = json.loads((tmp_path / "failed/run.json").read_bytes())
    assert run["status"] == "failed" and message in run["error"]
    with pytest.raises(ValueError):
        verify_backtest(tmp_path / "failed")


def test_replay_detects_tampered_metrics_even_with_rehashed_manifest(tmp_path: Path) -> None:
    catalog, parameters = fixture(tmp_path / "input")
    root = backtest(catalog, parameters, tmp_path / "run")
    result: dict[str, Any] = json.loads((root / "result.json").read_bytes())
    result["metrics"][0]["value"] = 100
    write_json(root / "result.json", result)
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["files"]["result.json"] = digest(root / "result.json")
    write_json(root / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Independent replay differs"):
        verify_backtest(root)


def test_replay_rejects_overview_that_disagrees_with_frozen_results(tmp_path: Path) -> None:
    catalog, parameters = fixture(tmp_path / "input")
    root = backtest(catalog, parameters, tmp_path / "run")
    overview = json.loads((root / "overview.json").read_bytes())
    overview["start"] = "2000-01-01"
    write_json(root / "overview.json", overview)
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["files"]["overview.json"] = digest(root / "overview.json")
    write_json(root / "manifest.json", manifest)
    with pytest.raises(ValueError, match="overview does not match frozen evidence"):
        verify_backtest(root)
