import json
from pathlib import Path

import pytest
from test_analysis import request

from dorislab_research.analysis_bundle import analyze
from dorislab_research.publish import export_analysis, publish


def test_export_keeps_evidence_separate_and_revisions_are_explicit(tmp_path: Path) -> None:
    source = tmp_path / "calculation"
    analyze(request(tmp_path), source)
    original = (source / "manifest.json").read_bytes()
    exported = export_analysis(source, tmp_path / "export")
    package = json.loads((exported / "artifact.json").read_bytes())
    assert package["data_nature"] == "synthetic"
    assert package["body"] == package["search"] == "report.md"
    assert len(package["files"]) > 8
    assert (source / "manifest.json").read_bytes() == original
    assert not (source / "artifact.json").exists()
    with pytest.raises(FileExistsError):
        export_analysis(source, exported)
    receipt = tmp_path / "receipt.json"
    reference = {"kind": "study", "id": "host-id", "version": "1"}
    receipt.write_text(json.dumps({"reference": reference}))
    with pytest.raises(ValueError, match="revision requires"):
        export_analysis(source, tmp_path / "revision", receipt)
    revised = export_analysis(source, tmp_path / "revision", receipt, "范围解释更正")
    assert json.loads((revised / "artifact.json").read_bytes())["previous"] == reference


def test_invalid_evidence_cannot_be_exported_and_missing_host_never_looks_registered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "calculation"
    analyze(request(tmp_path), source)
    (source / "result.json").write_text("{}")
    with pytest.raises(ValueError):
        export_analysis(source, tmp_path / "export")
    assert not (tmp_path / "export").exists()
    monkeypatch.delenv("DORISLAB_RESEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("DORISLAB_RESEARCH_CAPABILITY", raising=False)
    with pytest.raises(ValueError, match="unavailable"):
        publish(source)
    assert not (tmp_path / "calculation.receipt.json").exists()
