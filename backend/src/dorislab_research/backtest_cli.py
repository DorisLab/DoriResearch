"""Terminal-first strategy evaluation; host tools do not encode financial behavior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backtest_bundle import backtest, verify_backtest
from .backtest_publish import export_backtest, export_strategy
from .backtest_request import BacktestRequest

COMMANDS = {"backtest", "backtest-schema", "verify-backtest", "export-strategy", "export-backtest"}


def add_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    compute = sub.add_parser(
        "backtest", help="Evaluate monthly momentum on explicitly selected installed ETF daily data"
    )
    compute.add_argument("--catalog", required=True, type=Path)
    compute.add_argument("--request", required=True, type=Path)
    compute.add_argument("--output", required=True, type=Path)
    sub.add_parser("backtest-schema", help="Print the current strict daily ETF request schema")
    check = sub.add_parser(
        "verify-backtest", help="Verify immutable evidence and independently rerun the engine"
    )
    check.add_argument("--bundle", required=True, type=Path)
    strategy = sub.add_parser(
        "export-strategy", help="Export verified executable strategy evidence for host registration"
    )
    strategy.add_argument("--bundle", required=True, type=Path)
    strategy.add_argument("--output", required=True, type=Path)
    strategy.add_argument("--previous", type=Path)
    strategy.add_argument("--note", default="")
    run = sub.add_parser(
        "export-backtest", help="Export a verified run linked to its confirmed strategy version"
    )
    run.add_argument("--bundle", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--strategy-package", required=True, type=Path)
    run.add_argument("--strategy-receipt", required=True, type=Path)


def run(arguments: argparse.Namespace) -> None:
    if arguments.command == "backtest":
        print(backtest(arguments.catalog, arguments.request, arguments.output))
    elif arguments.command == "backtest-schema":
        print(json.dumps(BacktestRequest.model_json_schema(), ensure_ascii=False, indent=2))
    elif arguments.command == "verify-backtest":
        print(json.dumps(verify_backtest(arguments.bundle), ensure_ascii=False, indent=2))
    elif arguments.command == "export-strategy":
        print(
            export_strategy(arguments.bundle, arguments.output, arguments.previous, arguments.note)
        )
    else:
        print(
            export_backtest(
                arguments.bundle,
                arguments.output,
                arguments.strategy_package,
                arguments.strategy_receipt,
            )
        )
