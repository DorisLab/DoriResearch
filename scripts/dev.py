"""Run the real reader and SQLite service against disposable developer data."""

import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = root / "target" / "preview"
environment = {
    **os.environ,
    "DORIRESEARCH_TOKEN": secrets.token_hex(32),
    "PYTHONUTF8": "1",
}
for command in ("migrate", "seed"):
    subprocess.run(
        [
            sys.executable,
            "-m",
            "dorislab_research.service",
            command,
            "--data",
            str(data),
        ],
        check=True,
    )
service = subprocess.Popen(
    [sys.executable, "-m", "dorislab_research.service", "serve", "--data", str(data)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    env=environment,
    text=True,
)
assert service.stdout
environment["DORIRESEARCH_SERVICE_PORT"] = str(
    json.loads(service.stdout.readline())["port"]
)
try:
    subprocess.run(
        [
            shutil.which("node") or "node",
            "node_modules/vite/bin/vite.js",
            "--host",
            "127.0.0.1",
            "--port",
            "48121",
            "--strictPort",
        ],
        cwd=root / "frontend",
        env=environment,
        check=True,
    )
finally:
    if service.stdin:
        service.stdin.close()
    service.wait(timeout=10)
