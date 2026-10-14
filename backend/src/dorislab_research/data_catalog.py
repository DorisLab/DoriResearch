"""Compact discovery for terminal users; detailed manifests stay available on demand."""

from pathlib import Path
from typing import Any

from .local_data import describe


def catalog_summary(
    path: Path,
    selection: str | None = None,
    dataset: str | None = None,
    query: str | None = None,
    details: bool = False,
) -> dict[str, Any]:
    result = describe(path, selection, dataset)
    for item in result["selections"]:
        entries = [
            entry
            for entry in item["datasets"]
            if query is None
            or "".join(query.casefold().split())
            in "".join(
                f"{entry['view']['dataset_id']} {entry['view'].get('name', '')}".casefold().split()
            )
        ]
        if details:
            item["datasets"] = entries
        else:
            item["datasets"] = [
                {
                    **entry["view"],
                    "installed_dates": installed_dates(entry["files"]),
                    "file_count": len(entry["files"]),
                    "installed_bytes": sum(file["size_bytes"] for file in entry["files"]),
                }
                for entry in entries
            ]
            item["request"].pop("dataset_ids", None)
    result["selections"] = [item for item in result["selections"] if item["datasets"]]
    result["matching_datasets"] = sum(len(item["datasets"]) for item in result["selections"])
    if query is not None:
        result["query_scope"] = "dataset_id_or_name"
        if result["matching_datasets"] == 0:
            result["hint"] = (
                "查询仅匹配数据集名称或 ID，不搜索证券名称或代码；无匹配不表示缺少该证券数据。"
                "省略 --query 列出目录，或按 A股、ETF 等数据类型查询，"
                "再用 data-read 的 symbols 筛选证券。"
            )
    return result


def installed_dates(files: list[dict[str, Any]]) -> dict[str, str] | None:
    windows = [file["dates"] for file in files if file.get("dates")]
    if not windows:
        return None
    return {
        "start": min(window["start"] for window in windows),
        "end": max(window["end"] for window in windows),
    }
