import shutil
from pathlib import Path

import pytest

import dorislab_research
from dorislab_research.service_verify import verify


def test_verify_starts_real_service_reads_a_list_and_body_and_removes_isolated_data(
    tmp_path: Path,
) -> None:
    assert verify(tmp_path)["service"] == "passed"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", ["startup", "content"])
def test_candidate_startup_or_content_failure_is_rejected_before_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    candidate = tmp_path / "candidate"
    package = candidate / "dorislab_research"
    shutil.copytree(Path(dorislab_research.__file__).parent, package)
    target = package / ("service.py" if failure == "startup" else "service_api.py")
    source = target.read_text(encoding="utf-8")
    if failure == "startup":
        source = source.replace("server.serve_forever()", 'raise RuntimeError("broken candidate")')
    else:
        source = source.replace(
            '"content": lambda: library.content(reference)', '"content": lambda: {}'
        )
    target.write_text(source, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(candidate))
    data = tmp_path / "check"
    with pytest.raises(ValueError, match="候选工程服务验证失败"):
        verify(data)
    assert not list(data.iterdir())
