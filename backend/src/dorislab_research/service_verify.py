"""Exercise the candidate's real HTTP service using disposable data only."""

import json
import os
import queue
import secrets
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Any

from .database import migrate
from .library import Library, allocate


def verify(root: Path) -> dict[str, Any]:
    data = allocate(root).resolve()
    try:
        migrate(data)
        reference = Library(data).save(kind="study", title="启动校验", body="隔离阅读材料")
        return probe(data, reference)
    finally:
        if data.parent != root.resolve():
            raise ValueError("校验目录超出隔离根目录")
        shutil.rmtree(data)


def probe(data: Path, reference: dict[str, str]) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    with (data / "service.stderr").open("w+", encoding="utf-8") as errors:
        child = subprocess.Popen(
            [sys.executable, "-m", "dorislab_research.service", "serve", "--data", str(data)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            env={
                **os.environ,
                "DORIRESEARCH_TOKEN": token,
                "DORIRESEARCH_DATA": str(data),
                "PYTHONUTF8": "1",
            },
        )
        try:
            assert child.stdout and child.stdin
            output = child.stdout
            ready: queue.Queue[str] = queue.Queue()
            threading.Thread(target=lambda: ready.put(output.readline()), daemon=True).start()
            port = json.loads(ready.get(timeout=30))["port"]

            def rpc(operation: str, args: dict[str, Any]) -> Any:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/rpc",
                    data=json.dumps({"operation": operation, "args": args}).encode(),
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    value = json.load(response)
                if "error" in value:
                    raise ValueError(f"{operation}: {value['error']}")
                return value["result"]

            health = rpc("health", {})
            page = rpc("page", {"kind": "study", "query": "隔离阅读材料"})
            content = rpc("content", {"reference": reference})
            if not health.get("schema") or page["total"] != 1 or content["body"] != "隔离阅读材料":
                raise ValueError("健康检查、列表或正文读取结果不正确")
            return {"schema": health["schema"], "service": "passed"}
        except Exception as error:
            errors.flush()
            errors.seek(0)
            detail = errors.read(4096).replace(token, "[redacted]")
            raise ValueError(f"候选工程服务验证失败: {error}\n{detail}") from error
        finally:
            if child.stdin:
                child.stdin.close()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            if child.stdout:
                child.stdout.close()
