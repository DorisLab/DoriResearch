"""Run this editable project's CLI with Dorislab's managed Python and uv."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def command(arguments: list[str]) -> tuple[list[str], dict[str, str]]:
    uv = os.environ.get("DORISLAB_UV_BIN", "")
    root = os.environ.get("DORISLAB_RESEARCH_ENV_ROOT", "")
    if not uv or not Path(uv).is_absolute() or not Path(uv).is_file() or not root:
        raise RuntimeError("Dorislab 托管环境未配置，请重新检查客户端执行环境。独立开发见 README。")
    backend = Path(__file__).resolve().parent / "backend"
    identity = hashlib.sha256(str(backend).casefold().encode()).hexdigest()[:24]
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("UV_", "PYTHON"))
        and key.upper()
        not in {
            "VIRTUAL_ENV",
            "CONDA_PREFIX",
            "CONDA_DEFAULT_ENV",
            "DORIBT_NATIVE_RECORDS",
            "DORIBT_BUILD_NATIVE",
        }
    }
    env.update(
        {
            "UV_PROJECT_ENVIRONMENT": str(Path(root) / identity),
            "UV_CACHE_DIR": str(Path(root).parent / "cache"),
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
            "UV_PYTHON_DOWNLOADS": "never",
        }
    )
    entry = (
        arguments[1:] if arguments[:1] == ["python"] else ["-m", "dorislab_research", *arguments]
    )
    return [
        uv,
        "run",
        "--locked",
        "--no-dev",
        "--no-env-file",
        "--python",
        sys.executable,
        "--project",
        str(backend),
        "python",
        *entry,
    ], env


def main() -> int:
    try:
        args, env = command(sys.argv[1:])
        return subprocess.call(args, env=env)
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
