"""Discovery summarizes installed objects without hiding provenance or inventing coverage."""

import json
from pathlib import Path

from test_local_data import fixture

from dorislab_research.data_catalog import catalog_summary


def test_summary_separates_requested_declared_and_installed_dates(tmp_path: Path) -> None:
    path, _ = fixture(tmp_path)
    catalog = json.loads(path.read_bytes())
    entry = catalog["selections"][0]["plan"]["datasets"][0]
    entry["view"]["dates"] = {"start": "2020-01-01", "end": "2026-09-28"}
    entry["view"]["name"] = "A 股日线"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    summary = catalog_summary(path, query="A股")
    item = summary["selections"][0]
    dataset = item["datasets"][0]
    assert item["id"] == "a" * 64
    assert item["request"]["release_id"] == "c" * 64
    assert dataset["installed_dates"] == {"start": "2025-01-01", "end": "2025-01-31"}
    assert dataset["dates"]["start"] == "2020-01-01"
    assert dataset["file_count"] == 1
    assert dataset["installed_bytes"] == entry["files"][0]["size_bytes"]
    assert dataset["limitations"] == ["latest_corrected_not_point_in_time"]
    assert "files" not in dataset and "spec" not in dataset
    detailed = catalog_summary(path, dataset="test", details=True)
    assert detailed["selections"][0]["datasets"][0] == entry


def test_missing_matches_and_undated_objects_do_not_invent_a_range(tmp_path: Path) -> None:
    path, _ = fixture(tmp_path)
    assert catalog_summary(path, query="missing")["selections"] == []
    assert catalog_summary(path, dataset="unknown")["matching_datasets"] == 0
    catalog = json.loads(path.read_bytes())
    catalog["selections"][0]["plan"]["datasets"][0]["files"][0]["dates"] = None
    path.write_text(json.dumps(catalog), encoding="utf-8")
    assert (
        catalog_summary(path, query="TEST")["selections"][0]["datasets"][0]["installed_dates"]
        is None
    )


def test_unmatched_security_query_explains_catalog_scope(tmp_path: Path) -> None:
    path, _ = fixture(tmp_path)
    summary = catalog_summary(path, query="中际旭创")
    assert summary["matching_datasets"] == 0
    assert summary["query_scope"] == "dataset_id_or_name"
    assert "--query" in summary["hint"] and "symbols" in summary["hint"]
    assert catalog_summary(path)["matching_datasets"] == 1
