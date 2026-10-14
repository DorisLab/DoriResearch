"""Normalize the public engine result and independently reconcile its cash/holdings ledger."""

from typing import Any

import numpy as np
from doribt import BacktestResult

from .backtest_data import complete_months
from .backtest_metrics import calculate_metrics, drawdown_periods, month_returns
from .backtest_request import BacktestRequest


def validate_ledger(result: BacktestResult) -> None:
    equity = (result.holdings * result.close_units).sum(axis=1) + result.cash_units
    if not np.array_equal(equity, result.equity_units):
        raise ValueError("Account identity does not reconcile")
    if np.any(result.holdings < 0) or np.any(result.cash_units < 0):
        raise ValueError("Long-only/cash constraint violated")
    if (
        result.corporate_events
        or np.any(result.pending_shares)
        or np.any(result.dividend_receivable_units)
    ):
        raise ValueError("Unexpected corporate action in no-actions profile")
    if any(fill.reference_price_units is None for fill in result.fills):
        raise ValueError("Missing slippage reference price in the engine ledger")
    reconcile_fills(result)


def reconcile_fills(result: BacktestResult) -> None:
    orders = {o.order_id: o for o in result.orders}
    if len(orders) != len(result.orders) or len({f.fill_id for f in result.fills}) != len(
        result.fills
    ):
        raise ValueError("Duplicate order/fill identity")
    cash = round(result.initial_cash * 10000)
    holdings = dict.fromkeys(result.symbols, 0)
    fills_by_day: dict[str, list[Any]] = {}
    quantities = dict.fromkeys(orders, 0)
    for fill in result.fills:
        order = orders.get(fill.order_id)
        if order is None or (fill.symbol, fill.intent_id) != (order.symbol, order.intent_id):
            raise ValueError("Fill cannot be linked to its order/intent")
        quantities[fill.order_id] += fill.quantity
        fills_by_day.setdefault(fill.session.isoformat(), []).append(fill)
    for index, session in enumerate(result.sessions):
        for fill in fills_by_day.get(session.isoformat(), []):
            cash -= fill.quantity * fill.price_units
            cash -= fill.commission_units + fill.stamp_duty_units + fill.transfer_fee_units
            holdings[fill.symbol] += fill.quantity
        if (
            cash != result.cash_units[index]
            or list(holdings.values()) != result.holdings[index].tolist()
        ):
            raise ValueError("Cash/positions cannot be independently replayed from fills")
    if any(quantities[o.order_id] != o.filled for o in result.orders):
        raise ValueError("Order and fill quantities differ")


def account_rows(result: BacktestResult, request: BacktestRequest) -> list[dict[str, Any]]:
    start = result.sessions.index(request.start)
    if result.equity[start] != float(request.initial_cash) or np.any(result.holdings[start]):
        raise ValueError("Initial valuation must precede any execution; warmup cannot trade")
    previous = peak = float(request.initial_cash)
    rows = []
    for index in range(start, len(result.sessions)):
        day = result.sessions[index]
        fills = [f for f in result.fills if f.session == day]
        traded = sum(abs(f.quantity * f.price_units) for f in fills) / 10000
        value = float(result.equity[index])
        if value <= 0:
            raise ValueError("Non-positive valuation is unsupported by this profile")
        peak = max(peak, value)
        holding_value = float((result.holdings[index] * result.close_units[index]).sum() / 10000)
        rows.append(
            {
                "date": day.isoformat(),
                "initial": index == start,
                "equity": value,
                "cash": float(result.cash[index]),
                "holding_value": holding_value,
                "nav": value / float(request.initial_cash),
                "return": value / previous - 1,
                "drawdown": value / peak - 1,
                "exposure": holding_value / value,
                "cash_weight": float(result.cash[index]) / value,
                "traded_value": traded,
                "turnover": traded / previous / 2,
                "fees": sum(f.fees for f in fills),
            }
        )
        previous = value
    return rows


def normalize(
    result: BacktestResult, request: BacktestRequest, inputs: dict[str, Any]
) -> dict[str, Any]:
    validate_ledger(result)
    account = account_rows(result, request)
    positions = [
        {
            "date": day.isoformat(),
            "symbol": symbol,
            "quantity": int(result.holdings[i, j]),
            "value": int(result.holdings[i, j] * result.close_units[i, j]) / 10000,
            "weight": float(
                result.holdings[i, j] * result.close_units[i, j] / result.equity_units[i]
            ),
        }
        for i, day in enumerate(result.sessions)
        if day >= request.start
        for j, symbol in enumerate(result.symbols)
    ]
    fees = {
        name: sum(getattr(f, name + "_units") for f in result.fills) / 10000
        for name in ("commission", "stamp_duty", "transfer_fee")
    }
    normalized: dict[str, Any] = {
        "schema": "dorislab.backtest.result.v1",
        "account": account,
        "positions": positions,
        "drawdowns": drawdown_periods(account),
        "monthly": month_returns(account, complete_months(inputs, request)),
        "fees": fees,
        "fill_count": len(result.fills),
        "order_count": len(result.orders),
        "slippage_cost": sum(f.slippage_cost or 0 for f in result.fills),
        "slippage_accounting": "included in fill prices, never deducted a second time",
        "terminal": "mark_to_market_without_liquidation",
        "sample_role": "descriptive_no_search",
        "data_fingerprint": result.data_fingerprint,
        "benchmark": {
            "definition": request.benchmark,
            "cost": 0,
            "interest": 0,
            "curve": [{"date": r["date"], "nav": 1} for r in account]
            if request.benchmark == "cash_zero"
            else [],
        },
    }
    normalized["metrics"] = calculate_metrics(normalized, request)
    return normalized
