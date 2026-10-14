"""Chart CLI contracts; the managed launcher supplies the plotting dependencies."""

import argparse
import json
from pathlib import Path
from typing import Any


def add_commands(sub: Any) -> None:
    chart = sub.add_parser(
        "chart", help="Export a research chart using the shared Matplotlib theme"
    )
    chart.add_argument("--request", type=Path, required=True)
    chart.add_argument("--output", type=Path, required=True)
    sub.add_parser("chart-schema", help="Print the chart request JSON Schema")


def run(arguments: argparse.Namespace) -> None:
    from .charting import ChartRequest, export_chart

    if arguments.command == "chart-schema":
        print(json.dumps(ChartRequest.model_json_schema(), ensure_ascii=False))
    else:
        print(export_chart(arguments.request, arguments.output))
