import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from dorislab_research import datasets
from dorislab_research.database import migrate
from dorislab_research.library import Library
from dorislab_research.library_queries import archive, delete
from dorislab_research.search_sync import changes
from dorislab_research.service_api import dispatch


def test_search_deltas_include_file_edits_archive_restore_and_deleted_links(tmp_path: Path) -> None:
    migrate(tmp_path)
    library = Library(tmp_path)
    first = library.save(kind="study", title="题目", body="原文", summary="摘要")
    initial = changes(library, {})
    assert initial["reset"] and len(initial["documents"]) == 1
    assert "原文" in initial["documents"][0]["text"]
    assert changes(library, initial)["documents"] == []
    library.file(first, "report.md").write_text("文件直接修订", encoding="utf-8")
    changed = changes(library, initial)
    assert "文件直接修订" in changed["documents"][0]["text"]
    assert library.content(first)["body"] == "文件直接修订"
    archive(library, first, True)
    hidden = changes(library, changed)
    assert hidden["documents"][0]["item"] is None
    archive(library, first, False)
    restored = changes(library, hidden)
    assert restored["documents"][0]["item"]["title"] == "题目"
    archive(library, first, True)
    delete(library, [first["id"]])
    assert changes(library, restored)["documents"][0]["item"] is None
    assert dispatch(library, "status", {"reference": first})["summary"] == "摘要"


def test_rebuild_pagination_and_database_rollback(tmp_path: Path) -> None:
    migrate(tmp_path)
    library = Library(tmp_path)
    for index in range(53):
        library.save(kind="study", title=str(index), body="正文")
    page = changes(library, {})
    assert len(page["documents"]) == 50 and page["has_more"]
    last = changes(library, page)
    assert len(last["documents"]) == 3 and not last["has_more"] and not last["reset"]
    assert changes(library, {**last, "cursor": last["cursor"] + 1})["reset"]
    assert changes(library, {**last, "generation": "replaced"})["reset"]


@pytest.mark.parametrize("extension", ["csv", "json", "parquet"])
def test_pages_filter_sort_and_chart_ranges_cover_full_file(tmp_path: Path, extension: str) -> None:
    path = tmp_path / f"data.{extension}"
    values = [{"序号": i, "分类": "末尾" if i == 12002 else "普通"} for i in range(12003)]
    if extension == "json":
        path.write_text(json.dumps(values), encoding="utf-8")
    elif extension == "csv":
        path.write_text(
            "序号,分类\n" + "\n".join(f"{v['序号']},{v['分类']}" for v in values), encoding="utf-8"
        )
    else:
        cast(Callable[..., Any], pq.write_table)(pa.Table.from_pylist(values), path)
    result = datasets.table(path, {"query": "末尾"})
    assert result["total"] == 1 and int(result["rows"][0]["序号"]) == 12002
    result = datasets.table(path, {"sort": "序号", "descending": True, "page": 2})
    assert int(result["rows"][0]["序号"]) == 11982
    with pytest.raises(ValueError, match="10000"):
        datasets.rows(path)
    limited = datasets.rows(path, {"offset": 12000, "limit": 3, "columns": ["序号"]})
    assert [int(v["序号"]) for v in limited] == [12000, 12001, 12002]
    assert all(list(v) == ["序号"] for v in limited)


def test_stream_validation_cache_refresh_and_revision_bound_file_reads(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('[{"a":1},{"a":2}]', encoding="utf-8")
    assert datasets.table(path, {})["total"] == 2
    path.write_text('[{"b":3}]', encoding="utf-8")
    assert datasets.table(path, {})["columns"] == ["b"]
    for invalid in ('[{"b":3},]', "[1]", '[{"b":3}', '[{"b":3}]extra'):
        path.write_text(invalid, encoding="utf-8")
        with pytest.raises(ValueError):
            datasets.table(path, {})
    migrate(tmp_path)
    library = Library(tmp_path)
    path.write_bytes(b"a" * (4 * 1024 * 1024))
    item = library.save(kind="study", title="大文件", body="", files={"large.txt": path})
    args = {"reference": item, "path": "large.txt", "length": 16, "offset": 8}
    first = dispatch(library, "file_chunk", args)
    assert first["size"] == 4 * 1024 * 1024 and len(first["bytes"]) == 24
    library.file(item, "large.txt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="改变"):
        dispatch(library, "file_chunk", {**args, "revision": first["revision"]})
