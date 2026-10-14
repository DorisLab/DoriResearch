"""Reader behavior over real Parquet encoding, with explicitly synthetic market rows."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dorislab_research.local_data import describe, export_data, read_data
from dorislab_research.local_data_models import DataQuery


def fixture(tmp_path: Path, mode: str = "daily", duplicate: bool = False) -> tuple[Path, Path]:
    rows: list[dict[str, Any]] = [
        {"symbol": "ETF_A", "date": "2025-01-02", "end": "2025-01-03", "value": None},
        {"symbol": "ETF_A", "date": "2025-01-03", "end": None, "value": 12.0},
        {"symbol": "ETF_B", "date": "2025-01-03", "end": None, "value": 99.0},
    ]
    if duplicate:
        rows.append(rows[0])
    table = pa.Table.from_pylist(rows).replace_schema_metadata(
        {b"dorislab.availability.v1": b'{"synthetic":true,"missing":["value"]}'}
    )
    raw = tmp_path / "fixture.parquet"
    pq.write_table(table, raw)  # type: ignore[no-untyped-call]
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    obj = raw.replace(tmp_path / f"{digest}.parquet")
    window = {"start": "2025-01-01", "end": "2025-01-31"}
    dataset = {
        "view": {"dataset_id": "test", "limitations": ["latest_corrected_not_point_in_time"]},
        "spec": {
            "dataset_id": "test",
            "date_mode": mode,
            "date_column": "date",
            "end_column": "end",
            "end_exclusive": True,
            "symbol_column": "symbol",
            "primary_key": ["symbol", "date"],
            "columns": [{"name": name} for name in rows[0]],
        },
        "manifest_sha256": "b" * 64,
        "files": [
            {
                "sha256": digest,
                "size_bytes": obj.stat().st_size,
                "partition": "2025-01",
                "dates": window,
            }
        ],
    }
    catalog = {
        "schema": "dorislab.local-data.v1",
        "objects_root": str(tmp_path.resolve()),
        "agent_run_id": "synthetic-agent-run",
        "created_at_ms": 1,
        "selections": [
            {
                "id": "a" * 64,
                "plan": {
                    "request": {"release_id": "c" * 64, "dates": window, "dataset_ids": ["test"]},
                    "datasets": [dataset],
                },
            }
        ],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path, obj


def query(**changes: Any) -> DataQuery:
    return DataQuery.model_validate(
        {
            "selection": "a" * 64,
            "dataset": "test",
            "columns": ["date", "value"],
            "symbols": ["ETF_A"],
            **changes,
        }
    )


def test_nulls_selection_metadata_and_export_are_preserved(tmp_path: Path) -> None:
    path, _ = fixture(tmp_path)
    rows, proof = read_data(path, query())
    assert rows == [{"date": "2025-01-02", "value": None}, {"date": "2025-01-03", "value": 12}]
    assert proof["objects"][0]["availability"]["missing"] == ["value"]
    assert proof["view"]["limitations"] == ["latest_corrected_not_point_in_time"]
    assert proof["release_id"] == "c" * 64
    assert describe(path)["selections"][0]["id"] == "a" * 64
    request = tmp_path / "request.json"
    request.write_text(query().model_dump_json(), encoding="utf-8")
    output = export_data(path, request, tmp_path / "output")
    assert json.loads((output / "data.json").read_text()) == rows
    provenance = json.loads((output / "provenance.json").read_text())
    assert (
        provenance["output_sha256"]
        == hashlib.sha256((output / "data.json").read_bytes()).hexdigest()
    )
    with pytest.raises(FileExistsError):
        export_data(path, request, output)


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"selection": "d" * 64}, "no version substitution"),
        ({"dataset": "absent"}, "missing or ambiguous"),
        ({"columns": ["invented"]}, "columns are absent"),
        ({"start": "2024-12-31", "end": "2025-01-03"}, "exceed"),
        ({"max_rows": 1}, "no partial success"),
    ],
)
def test_invalid_reads_fail_without_fallback(
    tmp_path: Path, changes: dict[str, Any], message: str
) -> None:
    path, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match=message):
        read_data(path, query(**changes))


def test_corruption_missing_object_and_duplicate_rows_fail(tmp_path: Path) -> None:
    path, obj = fixture(tmp_path)
    data = obj.read_bytes()
    obj.write_bytes(b"X" + data[1:])
    with pytest.raises(ValueError, match="hash mismatch"):
        read_data(path, query())
    obj.unlink()
    with pytest.raises(FileNotFoundError):
        read_data(path, query())
    path, _ = fixture(tmp_path, duplicate=True)
    with pytest.raises(ValueError, match="Duplicate"):
        read_data(path, query())


def test_interval_boundary_and_snapshot_semantics(tmp_path: Path) -> None:
    path, _ = fixture(tmp_path, "interval")
    rows, _ = read_data(path, query(start="2025-01-03", end="2025-01-03"))
    assert rows == [{"date": "2025-01-03", "value": 12}]
    path, _ = fixture(tmp_path, "snapshot")
    with pytest.raises(ValueError, match="not historical"):
        read_data(path, query(start="2025-01-03", end="2025-01-03"))
    assert len(read_data(path, query())[0]) == 2


def test_old_catalog_keeps_version_when_host_selection_changes(tmp_path: Path) -> None:
    old, _ = fixture(tmp_path)
    updated = json.loads(old.read_bytes())
    updated["selections"][0]["id"] = "d" * 64
    new = tmp_path / "new-catalog.json"
    new.write_text(json.dumps(updated), encoding="utf-8")
    assert len(read_data(old, query())[0]) == 2
    with pytest.raises(ValueError, match="no version substitution"):
        read_data(new, query())


def test_cli_reads_the_same_catalog_and_emits_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dorislab_research.cli import main

    path, _ = fixture(tmp_path)
    request = tmp_path / "request.json"
    request.write_text(query().model_dump_json(), encoding="utf-8")
    output = tmp_path / "cli-output"
    monkeypatch.setattr(
        "sys.argv",
        [
            "dorislab-research",
            "data-read",
            "--catalog",
            str(path),
            "--request",
            str(request),
            "--output",
            str(output),
        ],
    )
    main()
    assert json.loads((output / "provenance.json").read_bytes())["row_count"] == 2
