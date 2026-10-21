import json
import time
from pathlib import Path

import pytest

from dorislab_research.database import migrate
from dorislab_research.examples import seed
from dorislab_research.jobs import job, start
from dorislab_research.library import ConflictError, Library
from dorislab_research.library_queries import archive, delete, listing, status
from dorislab_research.service_api import dispatch


@pytest.fixture
def library(tmp_path: Path) -> Library:
    migrate(tmp_path)
    return Library(tmp_path)


def test_save_conflict_is_detected_before_creating_files(library: Library) -> None:
    item = library.save(kind="study", title="研究", body="原结论", summary="摘要")
    changed = library.save(
        kind="study", title="更新", body="更新结论", id=item["id"], expected_revision=1
    )
    directories = list((library.root / "files").iterdir())
    with pytest.raises(ConflictError):
        library.save(
            kind="study", title="过期修改", body="错误", id=item["id"], expected_revision=1
        )
    assert list((library.root / "files").iterdir()) == directories
    assert library.content(item)["body"] == "原结论"
    assert library.content(changed)["body"] == "更新结论"
    assert listing(library, "更新结论")[0]["reference"] == changed


def test_deleted_reference_has_summary_but_search_and_related_content_survive(
    library: Library,
) -> None:
    study = library.save(kind="study", title="研究", body="正文", summary="原摘要")
    strategy = library.save(kind="strategy", title="策略", body="规则", references=[study])
    revised = library.save(
        id=study["id"],
        expected_revision=1,
        kind="study",
        title="研究修订",
        body="新正文",
        summary="新摘要",
    )
    archive(library, study, True)
    assert not listing(library, kind="study")
    assert library.content(study)["body"] == "正文"
    delete(library, [study["id"]])
    assert status(library, study)["summary"] == "原摘要"
    assert status(library, study)["deleted_at"]
    assert status(library, revised)["summary"] == "新摘要"
    delete(library, [study["id"]])
    assert status(library, study)["summary"] == "原摘要"
    assert library.content(strategy)["references"] == [study]
    with pytest.raises(ValueError, match="已被删除"):
        library.content(study)


def test_local_component_files_and_schema_upgrade_write_barrier(
    library: Library, tmp_path: Path
) -> None:
    values = tmp_path / "values.json"
    values.write_text(json.dumps([{"值": 2}, {"值": 1}]), encoding="utf-8")
    study = library.save(kind="study", title="表格", body="", files={"nested/values.json": values})
    table = dispatch(
        library, "table", {"reference": study, "path": "nested/values.json", "sort": "值"}
    )
    assert table["rows"] == [{"值": 1}, {"值": 2}]
    with pytest.raises(ValueError):
        library.file(study, "../../research.sqlite3")
    dispatch(library, "freeze", {})
    with pytest.raises(ValueError, match="升级"):
        library.save(kind="study", title="等待", body="")
    dispatch(library, "backup", {})
    assert (library.root / "activation.sqlite3").is_file()


def test_examples_are_computed_and_manual_result_is_independent(library: Library) -> None:
    seed(library)
    seed(library)
    assert len(listing(library)) == 2
    strategy = listing(library, kind="strategy")[0]["reference"]
    queued = start(library, strategy, {"parameters": {"cost_bps": 10, "position": 0.2}})
    deadline = time.monotonic() + 20
    while queued["status"] in ("running", "queued") and time.monotonic() < deadline:
        time.sleep(0.05)
        queued = job(library, queued["id"])
    assert queued["status"] == "succeeded", queued["error"]
    result = library.content(queued["result"])
    assert result["references"] == [strategy]
    assert "curve.parquet" in [item["path"] for item in result["files"]]
    assert len(listing(library, kind="run")) == 1
    study = listing(library, kind="study")[0]["reference"]
    archive(library, study, True)
    delete(library, [study["id"]])
    seed(library)
    assert not listing(library, kind="study")
