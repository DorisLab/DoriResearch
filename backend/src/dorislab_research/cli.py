"""Explicit CLI inputs, no .env loading or implicit access to user data."""

import argparse
import json
from pathlib import Path

from . import backtest_cli, chart_cli, data_cli, publish
from .analysis import AnalysisRequest
from .analysis_bundle import analyze, verify_analysis
from .doctor import inspect_project


def main() -> None:
    parser = argparse.ArgumentParser(description="Dorislab editable research engineering")
    sub = parser.add_subparsers(dest="command", required=True)
    data_cli.add_commands(sub)
    publish.add_commands(sub)
    backtest_cli.add_commands(sub)
    chart_cli.add_commands(sub)
    analysis = sub.add_parser("analyze", help="Analyze an explicitly sourced date/value CSV")
    analysis.add_argument("--request", required=True, type=Path)
    analysis.add_argument("--output", required=True, type=Path)
    check = sub.add_parser("verify-analysis", help="Check analysis evidence, values and report")
    check.add_argument("--bundle", required=True, type=Path)
    sub.add_parser("analysis-schema", help="Print the current analysis request JSON Schema")
    doctor = sub.add_parser("doctor", help="Check the current editable project layout")
    doctor.add_argument("--project", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.command in backtest_cli.COMMANDS:
        backtest_cli.run(arguments)
    elif arguments.command in {"chart", "chart-schema"}:
        chart_cli.run(arguments)
    else:
        run_existing(arguments)


def run_existing(arguments: argparse.Namespace) -> None:
    if arguments.command in {
        "export-analysis",
        "export-study",
        "study-schema",
        "publish",
        "save-study",
        "prepare-publication",
        "prepare-project",
    }:
        publish.run(arguments)
    elif arguments.command.startswith("data-"):
        data_cli.run(arguments)
    elif arguments.command == "analyze":
        print(analyze(arguments.request, arguments.output))
    elif arguments.command == "verify-analysis":
        print(verify_analysis(arguments.bundle).model_dump_json(indent=2))
    elif arguments.command == "analysis-schema":
        print(json.dumps(AnalysisRequest.model_json_schema(), ensure_ascii=False, indent=2))
    elif arguments.command == "doctor":
        result = inspect_project(arguments.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["ready"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
