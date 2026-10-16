import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from dorislab_research.database import migrate
from dorislab_research.examples import seed
from dorislab_research.library import Library
from dorislab_research.library_queries import listing


def test_real_service_parallel_parquet_reads_authentication_and_parent_lifetime(
    tmp_path: Path,
) -> None:
    migrate(tmp_path)
    seed(Library(tmp_path))
    reference = listing(Library(tmp_path), kind="study")[0]["reference"]
    child = subprocess.Popen(
        [sys.executable, "-m", "dorislab_research.service", "serve", "--data", str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "DORIRESEARCH_TOKEN": "test-service-only"},
    )
    try:
        assert child.stdout and child.stdin
        port = json.loads(child.stdout.readline())["port"]

        def rpc(operation: str, token: str = "test-service-only") -> dict[str, Any]:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/rpc",
                data=json.dumps(
                    {
                        "operation": operation,
                        "args": {
                            "reference": reference,
                            "path": "curve.parquet",
                        },
                    }
                ).encode(),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                return dict(json.load(response))

        with pytest.raises(urllib.error.HTTPError) as rejected:
            rpc("health", "wrong-token")
        assert rejected.value.code == 403
        with ThreadPoolExecutor(max_workers=2) as pool:
            curves, table = list(pool.map(rpc, ["rows", "table"]))
        assert len(curves["result"]) == table["result"]["total"] == 258
        assert len(table["result"]["rows"]) == 20
        assert rpc("health")["result"]["schema"] == "0002"
        child.stdin.close()
        assert child.wait(timeout=5) == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
