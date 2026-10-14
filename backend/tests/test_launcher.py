import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "run.py"


def test_launcher_requires_host_paths_even_if_user_has_uv(tmp_path: Path) -> None:
    env = dict(os.environ)
    env.pop("DORISLAB_UV_BIN", None)
    env["DORISLAB_RESEARCH_ENV_ROOT"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(LAUNCHER), "--help"],
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 1
    assert "托管环境未配置" in result.stderr


def test_launcher_isolates_user_python_and_uv_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uv = tmp_path / "uv.exe"
    uv.write_text("test executable identity")
    monkeypatch.setenv("DORISLAB_UV_BIN", str(uv))
    monkeypatch.setenv("DORISLAB_RESEARCH_ENV_ROOT", str(tmp_path / "projects"))
    for key in [
        "UV_PROJECT_ENVIRONMENT",
        "UV_PYTHON",
        "UV_INDEX_URL",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "DORIBT_NATIVE_RECORDS",
        "DORIBT_BUILD_NATIVE",
    ]:
        monkeypatch.setenv(key, "unrelated-user-environment")
    command, env = runpy.run_path(str(LAUNCHER))["command"](
        ["data-catalog", "--catalog", "a b.json"]
    )
    assert command[0] == str(uv)
    assert command[-3:] == ["data-catalog", "--catalog", "a b.json"]
    assert "--locked" in command and "--no-env-file" in command
    assert env["UV_PROJECT_ENVIRONMENT"].startswith(str(tmp_path / "projects"))
    assert not any("unrelated-user-environment" == value for value in env.values())
    script_command, script_env = runpy.run_path(str(LAUNCHER))["command"](
        ["python", "a b/compute.py", "--output", "new results"]
    )
    assert script_command[-4:] == ["python", "a b/compute.py", "--output", "new results"]
    assert "dorislab_research" not in script_command
    assert script_env == env
