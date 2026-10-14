"""Hand-calculated metric oracles, including cases where a number must not be invented."""

import math
from decimal import Decimal
from typing import Any

import pytest
from backtest_fixture import request

from dorislab_research.backtest_data import numeric_values
from dorislab_research.backtest_metrics import drawdown_periods, month_returns, risk_metrics
from dorislab_research.backtest_request import BacktestRequest


def test_risk_ratios_use_daily_excess_and_all_observations() -> None:
    req = BacktestRequest.model_validate(request())
    metrics = {m["metric_id"]: m for m in risk_metrics([0.1, -0.1], req)}
    assert metrics["annual_volatility"]["value"] == pytest.approx(math.sqrt(0.02 * 252))
    assert metrics["sharpe"]["value"] == pytest.approx(0)
    assert metrics["sortino"]["value"] == pytest.approx(0)
    req = req.model_copy(update={"target_return": 0.1, "risk_free_rate": 0.03})
    target, rf = 1.1 ** (1 / 252) - 1, 1.03 ** (1 / 252) - 1
    metrics = {m["metric_id"]: m for m in risk_metrics([0.1, -0.1], req)}
    assert metrics["sharpe"]["value"] == pytest.approx(-rf / math.sqrt(0.02) * math.sqrt(252))
    assert metrics["sortino"]["value"] == pytest.approx(
        -target / ((0.1 + target) / math.sqrt(2)) * math.sqrt(252)
    )
    values = {m["metric_id"]: m for m in risk_metrics([0.01], req)}
    assert values["annual_volatility"]["status"] == "undefined"
    assert values["sortino"]["status"] == "undefined"


def test_drawdown_recovery_censoring_and_partial_months() -> None:
    rows: list[dict[str, Any]] = [
        {"date": d, "equity": v, "drawdown": dd}
        for d, v, dd in [
            ("2025-01-30", 100, 0),
            ("2025-01-31", 90, -0.1),
            ("2025-02-03", 80, -0.2),
            ("2025-02-04", 100, 0),
            ("2025-02-28", 90, -0.1),
            ("2025-03-03", 95, -0.05),
        ]
    ]
    periods = drawdown_periods(rows)
    assert periods[0]["trading_days"] == 2 and periods[0]["recovery"] == "2025-02-04"
    assert periods[1]["trading_days"] == 2 and periods[1]["censored"] is True
    monthly = month_returns(rows, {"2025-02"})
    assert [m["complete"] for m in monthly] == [False, True, False]
    assert monthly[1]["return_rate"] == 0


def test_price_encoding_noise_is_distinct_from_an_off_tick_price() -> None:
    row = dict.fromkeys(("open", "high", "low", "close", "pre_close"), 2.1310000000000002)
    row["volume"] = 100
    assert numeric_values(row, Decimal(".001"))["close"] == Decimal("2.131")
    row["close"] = 2.13101
    with pytest.raises(ValueError, match="off the declared tick"):
        numeric_values(row, Decimal(".001"))
