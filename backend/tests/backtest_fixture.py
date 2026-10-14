"""Synthetic, explicitly identified Parquet inputs for failure and accounting tests."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from dorislab_research.backtest_data import DATASETS
from dorislab_research.bundles import digest, write_json


def request() -> dict[str, Any]:
    return {
        "title": "ETF 月度轮动账本验收",
        "selection": "a" * 64,
        "symbols": ["ETF_A"],
        "warmup_start": "2025-01-01",
        "start": "2025-01-10",
        "end": "2025-03-31",
        "parameters": {"lookback": 3, "top_n": 1, "max_exposure": "0.5"},
        "assumptions": {
            "label": "Synthetic test assumptions, not exchange rules",
            "price_tick": ".001",
            "lot_size": 100,
            "settlement_days": 1,
            "price_limit_ratio": ".1",
            "commission": ".0003",
            "minimum_commission": "5",
            "stamp_duty_sell": "0",
            "transfer_fee": "0",
            "slippage_bps": "2",
            "max_participation": ".05",
        },
        "benchmark": "none",
        "data_nature": "synthetic",
    }


def inputs() -> dict[str, list[dict[str, Any]]]:
    days = [(date(2025, 1, 1) + timedelta(days=n)) for n in range(90)]
    calendar = [
        {"trade_date": d.isoformat(), "exchange": "CN", "is_open": d.weekday() < 5} for d in days
    ]
    rows = []
    previous = 10.0
    for index, day in enumerate(d for d in days if d.weekday() < 5):
        closing = round(10 + min(index, 24) * 0.02 - max(index - 24, 0) * 0.03, 3)
        rows.append(
            {
                "trade_date": day.isoformat(),
                "symbol": "ETF_A",
                "open": previous,
                "close": closing,
                "low": round(min(previous, closing) - 0.01, 3),
                "high": round(max(previous, closing) + 0.01, 3),
                "pre_close": previous,
                "volume": 100000,
                "suspend_flag": 0,
                "adj_type": "none",
            }
        )
        previous = closing
    return {"calendar": calendar, "bars": rows, "actions": []}


def fixture(
    root: Path,
    data: dict[str, list[dict[str, Any]]] | None = None,
    parameters: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    data = data if data is not None else inputs()
    datasets: list[dict[str, Any]] = []
    dates = {"start": "2025-01-01", "end": "2025-03-31"}
    for key, (dataset, columns) in DATASETS.items():
        table = pa.Table.from_pylist(data[key]) if data[key] else pa.table({c: [] for c in columns})
        path = root / f"{key}.parquet"
        pq.write_table(table, path)  # type: ignore[no-untyped-call]
        sha = digest(path)
        path = path.replace(root / f"{sha}.parquet")
        datasets.append(
            {
                "view": {"dataset_id": dataset, "limitations": ["synthetic"]},
                "spec": {
                    "dataset_id": dataset,
                    "date_mode": "daily",
                    "date_column": "trade_date",
                    "symbol_column": None if key == "calendar" else "symbol",
                    "primary_key": ["trade_date", "exchange" if key == "calendar" else "symbol"],
                    "columns": [{"name": c} for c in columns],
                },
                "manifest_sha256": "b" * 64,
                "files": [
                    {
                        "sha256": sha,
                        "size_bytes": path.stat().st_size,
                        "partition": "fixture",
                        "dates": dates,
                    }
                ],
            }
        )
    catalog = root / "catalog.json"
    write_json(
        catalog,
        {
            "schema": "dorislab.local-data.v1",
            "agent_run_id": "fixture",
            "created_at_ms": 1,
            "objects_root": str(root.resolve()),
            "selections": [
                {
                    "id": "a" * 64,
                    "plan": {
                        "request": {
                            "release_id": "c" * 64,
                            "dates": dates,
                            "dataset_ids": [d["view"]["dataset_id"] for d in datasets],
                        },
                        "datasets": datasets,
                    },
                }
            ],
        },
    )
    request_file = root / "request.json"
    write_json(request_file, parameters or request())
    return catalog, request_file
