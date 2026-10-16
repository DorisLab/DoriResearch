"""Bounded record decoding. Large datasets never become a Python list."""

import csv
import math
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pyarrow.parquet as pq

from .json_records import JsonRecords

MAX_RECORD = 4 * 1024 * 1024


def json_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as stream:
        reader = JsonRecords(stream, MAX_RECORD)
        reader.consume("[")
        first = True
        while reader.token() != "]":
            if not first:
                reader.consume(",")
            yield reader.record()
            first = False
        reader.consume("]")
        if reader.token():
            raise ValueError("JSON 数组后包含多余内容")


def records(path: Path, columns: list[str] | None = None) -> Iterator[dict[str, Any]]:
    match path.suffix.lower():
        case ".parquet":
            with cast(Callable[..., Any], pq.ParquetFile)(path) as file:
                for batch in file.iter_batches(batch_size=1024, columns=columns):
                    yield from batch.to_pylist()
        case ".csv" | ".tsv":
            csv.field_size_limit(MAX_RECORD)
            with path.open(encoding="utf-8-sig", newline="") as stream:
                yield from csv.DictReader(
                    stream, delimiter="\t" if path.suffix.lower() == ".tsv" else ","
                )
        case ".json":
            yield from json_records(path)
        case _:
            raise ValueError("数据文件支持 JSON、CSV、TSV 和 Parquet")


def clean(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
