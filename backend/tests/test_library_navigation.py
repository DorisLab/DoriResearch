from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dorislab_research.database import migrate
from dorislab_research.library import Library
from dorislab_research.library_queries import archive, delete


def test_links_resolve_saved_bytes_after_work_file_removed(tmp_path: Path) -> None:
    migrate(tmp_path / "data")
    library = Library(tmp_path / "data")
    source = tmp_path / "strategy.py"
    source.write_text("original = 1", encoding="utf-8")
    path = "策略/[底仓] 网格#1%.py"
    ref = library.save(kind="strategy", title="策略 [验证]", body="", files={path: source})
    source.unlink()
    receipt = library.links(ref)
    file = next(file for file in receipt["files"] if file["path"] == path)
    assert parse_qs(urlsplit(file["url"]).query)["file"] == [path]
    assert library.file(ref, path).read_text(encoding="utf-8") == "original = 1"
    assert file["markdown"].startswith(r"[策略/\[底仓\] 网格#1%.py](<dorislab://")
    assert file["body_markdown"].endswith("%231%25.py>)")
    assert receipt == library.content(ref)["links"]


def test_navigation_is_bidirectional_current_and_does_not_rewrite_evidence(tmp_path: Path) -> None:
    migrate(tmp_path)
    library = Library(tmp_path)
    study = library.save(kind="study", title="底仓研究", body="旧结论")
    strategy = library.save(kind="strategy", title="原网格", body="", references=[study])
    revised = library.save(
        kind="strategy",
        title="完整的新策略名称",
        body="新规则",
        references=[study, strategy],
        id=strategy["id"],
        expected_revision=1,
    )
    run = library.save(kind="run", title="固定输入的结果", body="", references=[strategy])
    related = library.content(study)["related"]
    assert related == [{"reference": revised, "title": "完整的新策略名称", "unavailable": False}]
    assert library.content(run)["references"] == [strategy]
    assert library.content(run)["related"][0]["reference"] == revised
    assert library.content(strategy)["body"] == ""
    assert {item["reference"]["id"] for item in library.content(revised)["related"]} == {
        study["id"],
        run["id"],
    }
    archive(library, revised, True)
    assert library.content(study)["related"] == []
    delete(library, [revised["id"]])
    unavailable = library.content(run)["related"][0]
    assert unavailable["title"] == "完整的新策略名称"
    assert unavailable["unavailable"]
    assert library.content(run)["references"] == [strategy]
