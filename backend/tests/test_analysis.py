import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from dorislab_research.analysis import AnalysisRequest
from dorislab_research.analysis_bundle import analyze, verify_analysis
from dorislab_research.bundles import digest
from dorislab_research.doctor import inspect_project


def request(
    root: Path,
    csv: str = "\n".join(
        (
            "date,value",
            "2025-01-01,10",
            "2025-01-02,",
            "2025-01-03,30",
            "2025-01-04,20",
            "2025-02-01,100",
        )
    ),
) -> Path:
    (root / "input.csv").write_text(csv, encoding="utf-8")
    path = root / "request.json"
    path.write_text(
        AnalysisRequest(
            title="份额样本分析",
            question="范围内观察值如何变化？",
            input_file="input.csv",
            source_label="人工测试样本",
            data_nature="synthetic",
            unit="份",
            missing="drop",
            end=date(2025, 1, 31),
        ).model_dump_json(),
        encoding="utf-8",
    )
    return path


def test_analysis_preserves_scope_missing_policy_and_independent_evidence(tmp_path: Path) -> None:
    output = tmp_path / "result"
    source = request(tmp_path)
    analyze(source, output)
    result = verify_analysis(output)
    assert (result.observations, result.missing_count, result.excluded_count) == (3, 1, 1)
    assert (result.mean, result.sample_std, result.change, result.relative_change) == (
        20,
        10,
        10,
        1,
    )
    assert (output / "sources/uv.lock").is_file()
    assert "合成输入" in (output / "report.md").read_text(encoding="utf-8")
    (tmp_path / "input.csv").write_text("replaced user material")
    assert verify_analysis(output) == result
    with pytest.raises(FileExistsError):
        analyze(source, output)


def test_failed_attempt_is_preserved_and_retry_has_a_new_identity(tmp_path: Path) -> None:
    source = request(tmp_path, "date,value\n2025-01-01,NaN\n")
    failed = tmp_path / "failed"
    with pytest.raises(ValueError, match="Non-finite"):
        analyze(source, failed)
    record = json.loads((failed / "run.json").read_bytes())
    assert record["status"] == "failed"
    assert (failed / "input.csv").is_file()
    with pytest.raises(ValueError):
        verify_analysis(failed)
    retry = tmp_path / "retry"
    analyze(request(tmp_path), retry)
    assert json.loads((retry / "run.json").read_bytes())["id"] != record["id"]


def test_rehashed_incorrect_result_is_still_rejected(tmp_path: Path) -> None:
    output = tmp_path / "result"
    analyze(request(tmp_path), output)
    result = json.loads((output / "result.json").read_bytes())
    result["mean"] = 999
    (output / "result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="integrity"):
        verify_analysis(output)
    manifest = json.loads((output / "manifest.json").read_bytes())
    manifest["files"]["result.json"] = digest(output / "result.json")
    (output / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="frozen input"):
        verify_analysis(output)


@pytest.mark.parametrize("key", ["../outside.txt", "C:/outside.txt", "sources\\file.py"])
def test_manifest_cannot_refer_outside_bundle(tmp_path: Path, key: str) -> None:
    output = tmp_path / "result"
    analyze(request(tmp_path), output)
    manifest = json.loads((output / "manifest.json").read_bytes())
    manifest["files"][key] = "0" * 64
    (output / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe"):
        verify_analysis(output)


def test_zero_initial_value_and_required_source_declaration(tmp_path: Path) -> None:
    source = request(tmp_path, "date,value\n2025-01-01,0\n")
    output = tmp_path / "result"
    analyze(source, output)
    result = verify_analysis(output)
    assert result.relative_change is None and result.relative_change_reason
    assert result.sample_std is None
    data = json.loads(source.read_bytes())
    del data["data_nature"]
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_standalone_project_includes_its_rules_and_skills(tmp_path: Path) -> None:
    assert not inspect_project(tmp_path)["ready"]
    root = Path(__file__).parents[2]
    assert inspect_project(root)["ready"]
    for skill in (root / ".agents/skills").glob("*/SKILL.md"):
        assert "../../../docs/" in skill.read_text(encoding="utf-8")
