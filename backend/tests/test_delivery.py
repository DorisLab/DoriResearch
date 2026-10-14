import json
from pathlib import Path

import pytest
from test_study_export import request

from dorislab_research import delivery


def resumable_request(root: Path) -> Path:
    source = request(root)
    (root / "uv.lock").write_text("version = 1\n")
    value = json.loads(source.read_bytes())
    value["files"].append("uv.lock")
    value["execution"] = {
        "entrypoint": "compute.py",
        "parameters": [],
        "environment": ["uv.lock"],
        "data": [],
        "evidence": [],
        "instructions": "Run saved compute.py through the preserved project launcher.",
    }
    source.write_text(json.dumps(value))
    return source


def test_save_keeps_one_identity_after_lost_receipt_and_refuses_changed_materials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = resumable_request(tmp_path)
    output = tmp_path / "export"
    requests = []

    def submit(path: Path) -> dict[str, object]:
        package = json.loads((path / "artifact.json").read_bytes())
        requests.append(package["request_id"])
        if len(requests) == 1:
            raise ValueError("receipt lost")
        return {"request_id": requests[-1]}

    monkeypatch.setattr(delivery, "publish", submit)
    with pytest.raises(ValueError, match="receipt lost"):
        delivery.save_study(source, output)
    receipt = delivery.save_study(source, output)
    assert requests == [receipt["request_id"], receipt["request_id"]]
    (tmp_path / "compute.py").write_text("print(999)\n")
    with pytest.raises(ValueError, match="changed"):
        delivery.save_study(source, output)
    assert len(requests) == 2
    assert (output / "compute.py").read_text() == "print(1 + 2)\n"


@pytest.mark.parametrize("path", ["../compute.py", "missing.py", "uv.lock"])
def test_save_rejects_missing_escaped_or_duplicate_execution_paths(
    tmp_path: Path, path: str
) -> None:
    source = resumable_request(tmp_path)
    value = json.loads(source.read_bytes())
    value["execution"]["entrypoint"] = path
    source.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Execution paths"):
        delivery.save_study(source, tmp_path / "export")
    assert not (tmp_path / "export").exists()


def test_save_requires_explicit_materials_and_preserves_input_on_failure(tmp_path: Path) -> None:
    source = request(tmp_path)
    with pytest.raises(ValueError, match="requires execution"):
        delivery.save_study(source, tmp_path / "export")
    assert source.exists()
    assert not (tmp_path / "export").exists()
