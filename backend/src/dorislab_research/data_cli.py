"""Small terminal interface over the same Python reader; no model Tool registration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data_catalog import catalog_summary
from .local_data import export_data
from .local_data_models import DataQuery


def add_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    catalog = sub.add_parser("data-catalog", help="Describe a host-provided installed data catalog")
    catalog.add_argument("--catalog", required=True, type=Path)
    catalog.add_argument("--selection")
    catalog.add_argument("--dataset")
    catalog.add_argument(
        "--query", help="Match a dataset name or ID substring, not a security name or symbol"
    )
    catalog.add_argument(
        "--details", action="store_true", help="Include fields and object manifests"
    )
    read = sub.add_parser(
        "data-read", help="Read pinned local data with hash validation and provenance"
    )
    read.add_argument("--catalog", required=True, type=Path)
    read.add_argument("--request", required=True, type=Path)
    read.add_argument("--output", required=True, type=Path)
    sub.add_parser("data-schema", help="Print the local data query JSON Schema")


def run(arguments: argparse.Namespace) -> None:
    if arguments.command == "data-catalog":
        print(
            json.dumps(
                catalog_summary(
                    arguments.catalog,
                    arguments.selection,
                    arguments.dataset,
                    arguments.query,
                    arguments.details,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif arguments.command == "data-read":
        print(export_data(arguments.catalog, arguments.request, arguments.output))
    else:
        print(json.dumps(DataQuery.model_json_schema(), ensure_ascii=False, indent=2))
