"""Manual strategy execution. The callable is owned and configured by the strategy author."""

import json
import sys
import threading
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from . import job_process
from .database import connect, writable
from .library import Library, allocate


def job(library: Library, identity: str) -> dict[str, Any]:
    with connect(library.root) as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone()
    if not row:
        raise ValueError("回测任务不存在")
    result = dict(row)
    result["parameters"] = json.loads(result["parameters"])
    result["result"] = json.loads(result["result"]) if result["result"] else None
    return result


def start(library: Library, reference: dict[str, str], args: dict[str, Any]) -> dict[str, Any]:
    record = library.record(reference)
    saved = json.loads(record["config_json"])
    config = saved.get("backtest")
    if record["kind"] not in ("strategy", "run") or not config:
        raise ValueError("此策略尚未配置回测入口")
    parameters = prepare_parameters(config, args)
    identity = args.get("request_id") or str(uuid.uuid4())
    now = int(time.time() * 1000)
    with connect(library.root) as db:
        db.execute("BEGIN IMMEDIATE")
        writable(library.root)
        previous = db.execute("SELECT * FROM jobs WHERE id=?", (identity,)).fetchone()
        if previous:
            if (
                previous["strategy"] != reference["id"]
                or previous["revision"] != int(reference["version"])
                or json.loads(previous["parameters"]) != parameters
            ):
                raise ValueError("这次请求已用于其他回测，请发起新请求")
            return job(library, identity)
        db.execute(
            "INSERT INTO jobs VALUES (?,?,?,'queued',?,NULL,NULL,?,?)",
            (
                identity,
                reference["id"],
                int(reference["version"]),
                json.dumps(parameters),
                now,
                now,
            ),
        )
    threading.Thread(
        target=execute,
        args=(library, identity, record, config, parameters, args.get("_execution", {})),
        daemon=True,
    ).start()
    return job(library, identity)


def prepare_parameters(config: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    parameters = {item["name"]: item.get("default") for item in config.get("parameters", [])}
    parameters.update(args.get("parameters", {}))
    for key in ("start", "end"):
        if args.get(key):
            parameters[key] = args[key]
    bounds = config.get("date_range", {})
    for key in ("start", "end"):
        if bounds.get(key) and not parameters.get(key):
            parameters[key] = bounds[key]
    if bounds.get("start") and parameters.get("start", "") < bounds["start"]:
        raise ValueError("开始日期超出策略配置的数据范围")
    if bounds.get("end") and parameters.get("end", "") > bounds["end"]:
        raise ValueError("结束日期超出策略配置的数据范围")
    for key in ("start", "end"):
        if parameters.get(key):
            date.fromisoformat(parameters[key])
    if (
        parameters.get("start")
        and parameters.get("end")
        and parameters["start"] > parameters["end"]
    ):
        raise ValueError("开始日期不能晚于结束日期")
    return parameters


def execute(
    library: Library,
    identity: str,
    record: dict[str, Any],
    config: dict[str, Any],
    parameters: dict[str, Any],
    execution: dict[str, str],
) -> None:
    try:
        execute_inner(library, identity, record, config, parameters, execution)
    except Exception as error:
        update(library, identity, "failed", error=str(error))
    finally:
        job_process.forget(identity)


def execute_inner(
    library: Library,
    identity: str,
    record: dict[str, Any],
    config: dict[str, Any],
    parameters: dict[str, Any],
    execution: dict[str, str],
) -> None:
    directory = allocate(library.root / "executions")
    request = directory / "request.json"
    request.write_text(
        json.dumps(
            {"callable": config["callable"], "parameters": parameters, "output": str(directory)},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    update(library, identity, "running")
    try:
        # A separate process keeps imported strategy state and failures out of the reader service.
        command = [
            execution.get("python", sys.executable),
            "-m",
            "dorislab_research.worker",
            str(request),
        ]
        job_process.run(identity, command, directory, execution.get("source"))
        output = json.loads((directory / "result.json").read_text(encoding="utf-8"))

        def save_result() -> None:
            reference = save(library, record, config, parameters, execution, directory, output)
            update(library, identity, "succeeded", result=reference)

        job_process.finish(identity, save_result)
    except Exception as error:
        update(library, identity, "failed", error=str(error))


def save(
    library: Library,
    record: dict[str, Any],
    config: dict[str, Any],
    parameters: dict[str, Any],
    execution: dict[str, str],
    directory: Path,
    output: dict[str, Any],
) -> dict[str, str]:
    return library.save(
        kind="run",
        title=output.get("title", f"{record['title']} · 回测结果"),
        summary=output.get("summary", ""),
        body=output["body"],
        files={name: directory / name for name in output.get("files", [])},
        references=(
            json.loads(record["references_json"])
            if record["kind"] == "run"
            else [{"id": record["id"], "kind": "strategy", "version": str(record["revision"])}]
        ),
        config={
            "parameters": parameters,
            "backtest": config,
            "source_commit": execution.get("commit"),
        },
        data_nature=record["data_nature"],
        origin=record["origin"],
    )


def cancel(library: Library, identity: str) -> dict[str, Any]:
    with job_process.completion_lock():
        return cancel_locked(library, identity)


def cancel_locked(library: Library, identity: str) -> dict[str, Any]:
    with connect(library.root) as db:
        db.execute("BEGIN IMMEDIATE")
        writable(library.root)
        row = db.execute("SELECT status FROM jobs WHERE id=?", (identity,)).fetchone()
        if not row:
            raise ValueError("回测任务不存在")
        if row[0] in ("queued", "running"):
            job_process.cancel(identity)
            db.execute(
                "UPDATE jobs SET status='cancelled',error='你已取消这次回测' WHERE id=?",
                (identity,),
            )
    return job(library, identity)


def update(
    library: Library, identity: str, state: str, *, result: Any = None, error: str | None = None
) -> None:
    with connect(library.root) as db:
        db.execute(
            "UPDATE jobs SET status=?,result=?,error=?,updated_at=? "
            "WHERE id=? AND status!='cancelled'",
            (
                state,
                json.dumps(result) if result else None,
                error,
                int(time.time() * 1000),
                identity,
            ),
        )
