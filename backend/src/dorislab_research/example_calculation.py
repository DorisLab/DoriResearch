"""A deliberately synthetic execution-cost experiment, not evidence about real limit-up trading."""

import csv
import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def observations() -> list[dict[str, Any]]:
    rng = np.random.default_rng(20261016)
    values = []
    day = date(2025, 1, 1)
    for _ in range(360):
        if day.weekday() < 5:
            win = bool(rng.random() < 0.7)
            change = float(rng.uniform(0.003, 0.018) if win else -rng.uniform(0.025, 0.075))
            values.append({"日期": day.isoformat(), "假设毛收益": change, "获胜": win})
        day += timedelta(days=1)
    return values


def backtest(parameters: dict[str, Any], output: Path) -> dict[str, Any]:
    start = str(parameters.get("start", "2025-01-01"))
    end = str(parameters.get("end", "2025-12-26"))
    if start < "2025-01-01" or end > "2025-12-26" or start > end:
        raise ValueError("示例行情仅覆盖 2025-01-01 至 2025-12-26，请调整日期")
    cost = float(parameters.get("cost_bps", 10)) / 10000
    position = float(parameters.get("position", 0.2))
    if not 0 <= cost <= 0.01 or not 0 < position <= 1:
        raise ValueError("往返费用应在 0–100 基点，仓位应在 0–1 之间")
    data = [row for row in observations() if start <= row["日期"] <= end]
    if not data:
        raise ValueError("该区间没有示例交易日")
    nav, high = 1.0, 1.0
    curves = []
    for row in data:
        net = (row["假设毛收益"] - cost) * position
        nav *= 1 + net
        high = max(high, nav)
        curves.append({**row, "净收益": net, "净值": nav, "回撤": nav / high - 1, "仓位": position})
    cast(Callable[..., None], pq.write_table)(
        pa.Table.from_pylist(curves), output / "curve.parquet"
    )
    write_reading_table(curves, output / "trades.csv")
    (output / "parameters.json").write_text(
        json.dumps(parameters, ensure_ascii=False), encoding="utf-8"
    )
    chart = {
        "data": "curve.parquet",
        "option": {
            "xAxis": {"type": "category"},
            "yAxis": {"type": "value", "scale": True},
            "series": [
                {
                    "name": "策略净值",
                    "type": "line",
                    "showSymbol": False,
                    "encode": {"x": "日期", "y": "净值"},
                }
            ],
        },
    }
    (output / "nav.echarts.json").write_text(
        json.dumps(chart, ensure_ascii=False), encoding="utf-8"
    )
    wins = sum(row["净收益"] > 0 for row in curves)
    metrics = [
        {"label": "区间收益", "value": round((nav - 1) * 100, 2), "unit": "%"},
        {
            "label": "最大回撤",
            "value": round(min(row["回撤"] for row in curves) * 100, 2),
            "unit": "%",
        },
        {"label": "盈利交易占比", "value": round(wins / len(curves) * 100, 1), "unit": "%"},
        {"label": "交易次数", "value": len(curves), "unit": "次"},
    ]
    (output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
    body = result_body(nav, position, cost)
    return {
        "title": "高胜率也会亏钱 · 回测结果",
        "summary": (
            f"模拟数据区间收益 {(nav - 1) * 100:.2f}%，盈利交易占比 {wins / len(curves):.1%}。"
        ),
        "body": body,
        "files": [
            "curve.parquet",
            "trades.csv",
            "nav.echarts.json",
            "metrics.json",
            "parameters.json",
        ],
    }


def result_body(nav: float, position: float, cost: float) -> str:
    return f"""这次回测的区间收益是 **{(nav - 1) * 100:.2f}%**。
盈利交易占比高，仍可能亏钱；偶尔的大亏损可以吃掉许多次小盈利。

```metrics
{{"src":"metrics.json"}}
```

## 钱是怎样亏掉的

```echarts
{{"src":"nav.echarts.json"}}
```

每个模拟交易日按 {position:.0%} 仓位独立交易，往返费用 {cost * 10000:g} 基点。
这是为了说明胜率、盈亏比和费用的关系而生成的数据，不代表沪深市场实际打板表现。

## 每天发生了什么

```datatable
{{"src":"trades.csv"}}
```
"""


def write_reading_table(curves: list[dict[str, Any]], path: Path) -> None:
    """Reading values use explicit units; the calculation retains numeric Parquet columns."""
    columns = ["日期", "单笔毛收益（%）", "账户当日收益（%）", "账户净值", "回撤（%）", "仓位（%）"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for row in curves:
            writer.writerow(
                [
                    row["日期"],
                    round(row["假设毛收益"] * 100, 2),
                    round(row["净收益"] * 100, 2),
                    round(row["净值"], 4),
                    round(row["回撤"] * 100, 2),
                    round(row["仓位"] * 100, 1),
                ]
            )
