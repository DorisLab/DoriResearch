"""Read only host-selected immutable Parquet objects; never discover files by scanning caches."""

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .bundles import write_json
from .local_data_models import DataFile, DataQuery, Dataset, LocalCatalog, Selection


def load_catalog(path: Path) -> LocalCatalog:
    return LocalCatalog.model_validate_json(path.read_bytes())


def describe(
    path: Path, selection: str | None = None, dataset: str | None = None
) -> dict[str, Any]:
    catalog = load_catalog(path)
    selected = [item for item in catalog.selections if selection is None or item.id == selection]
    if selection and not selected:
        raise ValueError("Selection is not in this host catalog; refresh through Dorislab")
    return {
        "agent_run_id": catalog.agent_run_id,
        "created_at_ms": catalog.created_at_ms,
        "integrity": "Objects are verified when read; installed ranges do not prove continuity",
        "selections": [
            {
                "id": item.id,
                "request": item.plan.request.model_dump(mode="json"),
                "datasets": [
                    entry.model_dump(mode="json")
                    for entry in item.plan.datasets
                    if dataset is None or entry.view["dataset_id"] == dataset
                ],
            }
            for item in selected
        ],
    }


def choose(catalog: LocalCatalog, query: DataQuery) -> tuple[Selection, Dataset]:
    selection = next((s for s in catalog.selections if s.id == query.selection), None)
    if selection is None:
        raise ValueError("Requested selection is not installed; no version substitution")
    matches = [d for d in selection.plan.datasets if d.view["dataset_id"] == query.dataset]
    if len(matches) != 1:
        raise ValueError("Dataset is missing or ambiguous in the requested selection")
    dataset = matches[0]
    spec = dataset.spec
    if spec.get("dataset_id") != query.dataset:
        raise ValueError("Dataset specification identity mismatch")
    available = {column["name"] for column in spec["columns"]}
    if not set(query.columns) <= available:
        raise ValueError("Requested columns are absent from the dataset specification")
    if query.symbols and not spec.get("symbol_column"):
        raise ValueError("This dataset does not support a symbol filter")
    if spec["date_mode"] not in ("daily", "snapshot", "interval"):
        raise ValueError("Unsupported dataset date semantics")
    if spec["date_mode"] == "snapshot" and query.start is not None:
        raise ValueError("Snapshot data is not historical date-filtered data")
    dates = selection.plan.request.dates
    if query.start and query.end and (query.start < dates.start or query.end > dates.end):
        raise ValueError("Requested dates exceed this installed selection")
    return selection, dataset


def read_data(catalog_path: Path, query: DataQuery) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = load_catalog(catalog_path)
    selection, dataset = choose(catalog, query)
    spec = dataset.spec
    start = query.start or selection.plan.request.dates.start
    end = query.end or selection.plan.request.dates.end
    files = [f for f in dataset.files if relevant(f, spec["date_mode"], start, end)]
    if not files:
        raise ValueError("No local objects cover the requested window")
    if sum(f.size_bytes for f in files) > 512 * 1024 * 1024:
        raise ValueError("Read exceeds 512 MiB; select a narrower window")
    needed = list(
        dict.fromkeys(
            query.columns
            + spec["primary_key"]
            + [
                name
                for name in (
                    spec.get("date_column"),
                    spec.get("end_column"),
                    spec.get("symbol_column"),
                )
                if name
            ]
        )
    )
    rows: list[dict[str, Any]] = []
    identities: set[tuple[Any, ...]] = set()
    evidence: list[dict[str, Any]] = []
    for file in files:
        parquet = verified_parquet(catalog.objects_root, file)
        metadata = parquet.schema_arrow.metadata or {}
        availability = metadata.get(b"dorislab.availability.v1")
        evidence.append(
            {
                **file.model_dump(mode="json"),
                "availability": json.loads(availability) if availability else None,
            }
        )
        if not set(needed) <= set(parquet.schema_arrow.names):
            raise ValueError("Parquet columns do not match the requested specification")
        for batch in parquet.iter_batches(batch_size=8192, columns=needed):
            for row in batch.to_pylist():
                if not matches(row, query, spec, start, end):
                    continue
                identity = tuple(row[key] for key in spec["primary_key"])
                if identity in identities or any(value is None for value in identity):
                    raise ValueError("Duplicate or missing primary key in selected objects")
                identities.add(identity)
                rows.append({column: row[column] for column in query.columns})
                if len(rows) > query.max_rows:
                    raise ValueError("Row limit exceeded; narrow the request, no partial success")
    evidence_summary = {
        "schema": "dorislab.data-read.v1",
        "query": query.model_dump(mode="json"),
        "agent_run_id": catalog.agent_run_id,
        "selection": selection.id,
        "release_id": selection.plan.request.release_id,
        "manifest_sha256": dataset.manifest_sha256,
        "spec": spec,
        "view": dataset.view,
        "objects": evidence,
        "row_count": len(rows),
        "nulls_preserved": True,
        "coverage": "observed rows only; range endpoints do not prove continuous availability",
    }
    return rows, evidence_summary


def relevant(file: DataFile, mode: str, start: date, end: date) -> bool:
    return (
        mode != "daily"
        or file.dates is None
        or (file.dates.start <= end and file.dates.end >= start)
    )


def verified_parquet(root: Path, file: DataFile) -> Any:
    path = root / (file.sha256 + ".parquet")
    # Windows package virtualization can give the same directory different resolved
    # spellings for the root and its children. Compare filesystem identity, while
    # still rejecting redirected objects and parents outside the supplied root.
    if path.is_symlink() or path.is_junction() or not root.samefile(path.resolve().parent):
        raise ValueError("Data object path is linked or escapes the host catalog")
    if path.stat().st_size != file.size_bytes:
        raise ValueError("Local data object size mismatch; repair through Dorislab data settings")
    data = path.read_bytes()
    if len(data) != file.size_bytes or hashlib.sha256(data).hexdigest() != file.sha256:
        raise ValueError("Local data object hash mismatch; repair through Dorislab data settings")
    # PyArrow 24 ships this constructor without a typed signature.
    return pq.ParquetFile(pa.BufferReader(data))  # type: ignore[no-untyped-call]


def day(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def matches(
    row: dict[str, Any], query: DataQuery, spec: dict[str, Any], start: date, end: date
) -> bool:
    if query.symbols and row[spec["symbol_column"]] not in query.symbols:
        return False
    if spec["date_mode"] == "snapshot":
        return True
    first = day(row[spec["date_column"]])
    if spec["date_mode"] == "daily":
        return start <= first <= end
    last = row[spec["end_column"]]
    after_start = last is None or (
        day(last) > start if spec.get("end_exclusive") else day(last) >= start
    )
    return first <= end and after_start


def export_data(catalog: Path, request: Path, output: Path) -> Path:
    query = DataQuery.model_validate_json(request.read_bytes())
    rows, provenance = read_data(catalog, query)
    # JSON preserves null values, unlike an ambiguous blank CSV cell.
    data = json.dumps(rows, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    output.mkdir(parents=True, exist_ok=False)
    (output / "data.json").write_bytes(data)
    provenance["output_sha256"] = hashlib.sha256(data).hexdigest()
    provenance["reader_version"] = "dorislab.local-data.v1"
    write_json(output / "provenance.json", provenance)
    return output.resolve()
