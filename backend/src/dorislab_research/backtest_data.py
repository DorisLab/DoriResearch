"""Hash-checked installed data -> explicit DoriBT facts; no implicit gap filling."""

import json
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from doribt import Instrument, MarketData, RuleBook, RulePeriod, TradingRule

from .backtest_request import BacktestRequest
from .bundles import write_json
from .local_data import read_data
from .local_data_models import DataQuery

DATASETS = {
    "bars": (
        "raw/market/bars_1d_etf",
        [
            "trade_date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "pre_close",
            "suspend_flag",
            "adj_type",
        ],
    ),
    "calendar": ("raw/reference/trade_calendar", ["trade_date", "exchange", "is_open"]),
    "actions": (
        "raw/market/etf_divid_factor",
        [
            "trade_date",
            "symbol",
            "interest",
            "stock_bonus",
            "stock_gift",
            "allot_num",
            "allot_price",
            "gugai",
            "dr",
        ],
    ),
}


def freeze_inputs(catalog: Path, request: BacktestRequest, root: Path) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for key, (dataset, columns) in DATASETS.items():
        query = DataQuery(
            selection=request.selection,
            dataset=dataset,
            columns=columns,
            symbols=[] if key == "calendar" else request.symbols,
            start=request.warmup_start,
            end=request.end,
            max_rows=200000,
        )
        rows, proof = read_data(catalog, query)
        inputs[key] = json.loads(json.dumps(rows, default=str, allow_nan=False))
        write_json(root / f"{key}-provenance.json", proof)
    write_json(root / "input.json", inputs)
    return inputs


def sessions_from(inputs: dict[str, Any], request: BacktestRequest) -> list[str]:
    calendar = [r for r in inputs["calendar"] if r["exchange"] == "CN"]
    days = {r["trade_date"]: r["is_open"] for r in calendar}
    expected = {
        (request.warmup_start + timedelta(days=n)).isoformat()
        for n in range((request.end - request.warmup_start).days + 1)
    }
    if len(days) != len(calendar) or set(days) != expected:
        raise ValueError("CN calendar is missing days or has duplicates; no weekday fallback")
    if any(not isinstance(v, bool) for v in days.values()):
        raise ValueError("Calendar is_open must explicitly be boolean")
    sessions = sorted(d for d, opened in days.items() if opened)
    if request.start.isoformat() not in sessions or request.end.isoformat() not in sessions:
        raise ValueError("Initial valuation and end must be actual open sessions")
    if sessions.index(request.start.isoformat()) < request.parameters.lookback:
        raise ValueError("Insufficient pre-start warmup observations")
    return sessions


def checked_bars(
    inputs: dict[str, Any], request: BacktestRequest, sessions: list[str]
) -> list[dict[str, Any]]:
    if inputs["actions"]:
        raise ValueError("Corporate actions present: this profile cannot model their settlement")
    rows = sorted(inputs["bars"], key=lambda r: (r["trade_date"], r["symbol"]))
    keys = {(r["trade_date"], r["symbol"]) for r in rows}
    if len(keys) != len(rows) or keys != {(d, s) for d in sessions for s in request.symbols}:
        raise ValueError(
            "Missing/extra/duplicate ETF bars; no forward fill or universe substitution"
        )
    previous: dict[str, Decimal] = {}
    records = []
    for row in rows:
        symbol = row["symbol"]
        if row["adj_type"] != "none" or row["suspend_flag"] not in (0, 1):
            raise ValueError("Unconfirmed adjustment or suspension state")
        values = numeric_values(row, request.assumptions.price_tick)
        if symbol in previous and values["pre_close"] != previous[symbol]:
            raise ValueError(
                "Previous close mismatch: possible corporate action or missing history"
            )
        previous[symbol] = values["close"]
        records.append(convert_bar(row, values, request))
    return records


def numeric_values(row: dict[str, Any], tick: Decimal) -> dict[str, Decimal]:
    try:
        values = {
            k: Decimal(str(row[k])) for k in ("open", "high", "low", "close", "volume", "pre_close")
        }
    except InvalidOperation as error:
        raise ValueError("Missing/non-numeric market values") from error
    if any(not v.is_finite() or v < 0 for v in values.values()) or values["pre_close"] <= 0:
        raise ValueError("Missing/non-finite/negative market values")
    for key in ("open", "high", "low", "close", "pre_close"):
        canonical = (values[key] / tick).quantize(Decimal(1), rounding=ROUND_HALF_UP) * tick
        # Remove only binary-double encoding noise, never round a genuinely off-tick price.
        if abs(values[key] - canonical) > Decimal("1e-10"):
            raise ValueError("Market price is off the declared tick")
        values[key] = canonical
    return values


def convert_bar(
    row: dict[str, Any], values: dict[str, Decimal], request: BacktestRequest
) -> dict[str, Any]:
    tick, ratio = request.assumptions.price_tick, request.assumptions.price_limit_ratio
    limits = [
        (values["pre_close"] * (1 + direction * ratio) / tick).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
        * tick
        for direction in (1, -1)
    ]
    # Published volume is in lots of 100 shares, independent of the assumed order lot size.
    volume = values["volume"] * 100
    integral_volume = volume.to_integral_value(rounding=ROUND_HALF_UP)
    if abs(volume - integral_volume) > Decimal("1e-6"):
        raise ValueError("Market volume cannot be converted exactly to shares")
    return {
        "session": row["trade_date"],
        "symbol": row["symbol"],
        "status": "suspended" if row["suspend_flag"] == 1 else "trading",
        **{k: str(values[k]) for k in ("open", "high", "low", "close")},
        "volume": int(integral_volume),
        "upper_limit": str(limits[0]),
        "lower_limit": str(limits[1]),
    }


def market_from(inputs: dict[str, Any], request: BacktestRequest) -> MarketData:
    sessions = sessions_from(inputs, request)
    a = request.assumptions
    rule = TradingRule(
        price_tick=a.price_tick,
        buy_minimum=a.lot_size,
        buy_step=a.lot_size,
        sell_minimum=a.lot_size,
        sell_step=a.lot_size,
        settlement_days=a.settlement_days,
        stamp_duty_sell=a.stamp_duty_sell,
        transfer_fee=a.transfer_fee,
        instrument_kind="etf",
    )
    rules = RuleBook(
        tuple(
            RulePeriod(
                symbol=s,
                start=sessions[0],
                end=sessions[-1],
                rule=rule,
                source=a.label,
                version="declared-research-assumptions-v1",
            )
            for s in request.symbols
        )
    )
    return MarketData.from_records(
        checked_bars(inputs, request, sessions),
        calendar=sessions,
        instruments=[Instrument(symbol=s, kind="etf") for s in request.symbols],
        rules=rules,
        source=f"Dorislab installed selection {request.selection}; "
        "latest corrected prices, declared hypothetical execution rules",
    )


def complete_months(inputs: dict[str, Any], request: BacktestRequest) -> set[str]:
    # A return requires the preceding valuation. Unknown days after end cannot prove a full month.
    days = {r["trade_date"]: r["is_open"] for r in inputs["calendar"] if r["exchange"] == "CN"}
    result = set()
    for month in {d[:7] for d in days}:
        first = date.fromisoformat(month + "-01")
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        dates = [(first + timedelta(days=n)).isoformat() for n in range((next_month - first).days)]
        if all(d in days for d in dates):
            opened = [d for d in dates if days[d]]
            if (
                opened
                and request.start.isoformat() < opened[0]
                and opened[-1] <= request.end.isoformat()
            ):
                result.add(month)
    return result
