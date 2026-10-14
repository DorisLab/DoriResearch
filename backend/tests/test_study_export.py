import json
from pathlib import Path

import pytest

from dorislab_research.bundles import digest
from dorislab_research.study_export import export_study


def request(root: Path) -> Path:
    (root / "report.md").write_text("# 分组比较\n\n实际计算及局限。", encoding="utf-8")
    (root / "compute.py").write_text("print(1 + 2)\n", encoding="utf-8")
    path = root / "request.json"
    path.write_text(
        json.dumps(
            {
                "title": "分组比较",
                "summary": "观察到不同分组的差异",
                "data_nature": "real",
                "files": ["report.md", "compute.py"],
                "reproduction": "python compute.py",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_arbitrary_study_preserves_code_and_supports_explicit_revisions(tmp_path: Path) -> None:
    source = request(tmp_path)
    target = export_study(source, tmp_path / "export")
    package = json.loads((target / "artifact.json").read_bytes())
    assert package["project_format"] == "dorislab.study.v1"
    assert {f["path"] for f in package["files"]} == {"report.md", "compute.py", "study.json"}
    for file in package["files"]:
        assert digest(target / file["path"]) == file["sha256"]
    (tmp_path / "compute.py").write_text("print(999)\n")
    assert (target / "compute.py").read_text() == "print(1 + 2)\n"
    with pytest.raises(FileExistsError):
        export_study(source, target)
    previous = tmp_path / "receipt.json"
    reference = {"kind": "study", "id": "previous", "version": "1"}
    previous.write_text(json.dumps({"reference": reference}))
    with pytest.raises(ValueError, match="revision"):
        export_study(source, tmp_path / "revision", previous)
    revised = export_study(source, tmp_path / "revision", previous, "更新解释")
    assert json.loads((revised / "artifact.json").read_bytes())["previous"] == reference


@pytest.mark.parametrize(
    "files",
    [
        ["../outside.md"],
        ["report.md", "missing.py"],
        ["report.md", "REPORT.md"],
        ["report.md", "artifact.json"],
        ["report.md", "nested/../compute.py"],
    ],
)
def test_invalid_material_is_rejected_before_creating_package(
    tmp_path: Path, files: list[str]
) -> None:
    source = request(tmp_path)
    value = json.loads(source.read_bytes())
    value["files"] = files
    source.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        export_study(source, tmp_path / "export")
    assert not (tmp_path / "export").exists()
