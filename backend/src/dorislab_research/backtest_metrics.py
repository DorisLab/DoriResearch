"""Project metric definitions, separate from and retaining the engine's original statistics."""

import math
from datetime import date
from typing import Any

import numpy as np

from .backtest_request import BacktestRequest

DEFINITION = "dorislab.research.metrics.v1"


def metric(
    name: str,
    value: float | int | None,
    unit: str,
    reason: str = "",
    *,
    status: str = "undefined",
    **parameters: Any,
) -> dict[str, Any]:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"Non-finite metric: {name}")
    return {
        "metric_id": name,
        "definition_version": DEFINITION,
        "value": value,
        "unit": unit,
        "status": "computed" if value is not None else status,
        "reason": reason,
        "scope": "evaluation",
        "source_refs": ["result.json", "request.json"],
        "parameters": parameters,
    }


def risk_metrics(returns: list[float], request: BacktestRequest) -> list[dict[str, Any]]:
    values = np.asarray(returns, dtype=float)
    count = len(values)
    volatility = float(np.std(values, ddof=1)) if count >= 2 else None
    risk_free = (1 + request.risk_free_rate) ** (1 / 252) - 1
    target = (1 + request.target_return) ** (1 / 252) - 1
    downside = float(np.sqrt(np.mean(np.minimum(values - target, 0) ** 2))) if count else 0
    sharpe = (
        float(np.mean(values - risk_free) / volatility * math.sqrt(252)) if volatility else None
    )
    sortino = float(np.mean(values - target) / downside * math.sqrt(252)) if downside else None
    return [
        metric(
            "annual_volatility",
            volatility * math.sqrt(252) if volatility is not None else None,
            "ratio",
            "" if count >= 2 else "fewer than two daily returns",
            samples=count,
            ddof=1,
            periods=252,
        ),
        metric(
            "sharpe",
            sharpe,
            "ratio",
            "" if sharpe is not None else "insufficient returns or zero variance",
            annual_risk_free=request.risk_free_rate,
            samples=count,
            periods=252,
        ),
        metric(
            "sortino",
            sortino,
            "ratio",
            "" if sortino is not None else "no downside observations",
            annual_target=request.target_return,
            denominator="all daily observations",
            samples=count,
            periods=252,
        ),
    ]


def drawdown_periods(account: list[dict[str, Any]]) -> list[dict[str, Any]]:
    periods, active = [], None
    peak_date = account[0]["date"]
    for row in account[1:]:
        if row["drawdown"] < 0:
            if active is None:
                active = {
                    "peak": peak_date,
                    "start": row["date"],
                    "trough": row["date"],
                    "depth": row["drawdown"],
                    "trading_days": 0,
                    "recovery": None,
                    "censored": True,
                }
            active["trading_days"] += 1
            if row["drawdown"] < active["depth"]:
                active.update(trough=row["date"], depth=row["drawdown"])
        else:
            peak_date = row["date"]
            if active is not None:
                active.update(recovery=row["date"], censored=False)
                periods.append(active)
                active = None
    if active is not None:
        periods.append(active)
    return periods


def month_returns(account: list[dict[str, Any]], complete: set[str]) -> list[dict[str, Any]]:
    months: dict[str, dict[str, Any]] = {}
    for previous, row in zip(account, account[1:], strict=False):
        month = row["date"][:7]
        if month not in months:
            months[month] = {
                "month": month,
                "initial_equity": previous["equity"],
                "complete": month in complete,
            }
        months[month]["final_equity"] = row["equity"]
    return [
        dict(row, return_rate=row["final_equity"] / row["initial_equity"] - 1)
        for row in months.values()
    ]


def calculate_metrics(result: dict[str, Any], request: BacktestRequest) -> list[dict[str, Any]]:
    account = result["account"]
    initial, terminal = account[0]["equity"], account[-1]["equity"]
    days = (date.fromisoformat(account[-1]["date"]) - date.fromisoformat(account[0]["date"])).days
    annual = (terminal / initial) ** (365.25 / days) - 1 if days > 0 and terminal >= 0 else None
    monthly = [r["return_rate"] for r in result["monthly"] if r["complete"]]
    exposure = [r["exposure"] for r in account[1:]]
    turnovers = [r["turnover"] for r in account[1:]]
    fees = result["fees"]
    metrics = [
        metric("total_return", terminal / initial - 1, "ratio"),
        metric(
            "annual_return",
            annual,
            "ratio",
            "" if annual is not None else "invalid duration or terminal equity",
            calendar_days=days,
            short_sample=days < 365,
            year_days=365.25,
        ),
        metric(
            "max_drawdown",
            -min(r["drawdown"] for r in account),
            "ratio",
            sign="positive loss magnitude",
        ),
        metric(
            "longest_underwater",
            max((r["trading_days"] for r in result["drawdowns"]), default=0),
            "trading_days",
            censored_at_end=account[-1]["drawdown"] < 0,
        ),
        metric(
            "worst_complete_month",
            min(monthly) if monthly else None,
            "ratio",
            "" if monthly else "no proven complete calendar month",
            samples=len(monthly),
        ),
        metric(
            "average_exposure", float(np.mean(exposure)), "ratio", weighting="equal daily close"
        ),
        metric("maximum_exposure", max(exposure), "ratio"),
        metric("one_way_turnover", sum(turnovers), "ratio", divisor=2, includes_initial_build=True),
        metric(
            "annual_turnover",
            sum(turnovers) * 365.25 / days if days else None,
            "ratio",
            calendar_days=days,
        ),
        metric("traded_value", sum(r["traded_value"] for r in account), "CNY"),
        metric("fill_count", result["fill_count"], "count"),
        metric("order_count", result["order_count"], "count"),
        metric("fees", sum(fees.values()), "CNY", components=fees),
    ]
    metrics.extend(risk_metrics([r["return"] for r in account[1:]], request))
    metrics.append(
        metric(
            "benchmark_return",
            0 if request.benchmark == "cash_zero" else None,
            "ratio",
            "" if request.benchmark == "cash_zero" else "no benchmark selected",
            status="not_applicable",
            definition=request.benchmark,
        )
    )
    return metrics
