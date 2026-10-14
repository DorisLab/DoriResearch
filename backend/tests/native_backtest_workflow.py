"""Run by the Rust native acceptance in an isolated, capability-bearing Agent terminal."""

import json
import runpy
import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).parent
    project = root / "fixture project"
    launcher = project / "run.py"
    results = root / "research/results"
    results.mkdir(parents=True, exist_ok=True)
    args, environment = runpy.run_path(str(launcher))["command"]([])
    generator = project / "backend/tests/backtest_fixture.py"
    source = (
        "import runpy,sys; from pathlib import Path; "
        "runpy.run_path(sys.argv[1])['fixture'](Path(sys.argv[2]))"
    )
    subprocess.run(
        [*args[:-2], "-c", source, str(generator), str(root / "input")], env=environment, check=True
    )

    def run(*arguments: str | Path) -> str:
        completed = subprocess.run(
            [sys.executable, str(launcher), *map(str, arguments)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr)
        return completed.stdout

    run(
        "backtest",
        "--catalog",
        root / "input/catalog.json",
        "--request",
        root / "input/request.json",
        "--output",
        results / "calculation",
    )
    run("export-strategy", "--bundle", results / "calculation", "--output", results / "strategy")
    strategy = json.loads(run("publish", "--package", results / "strategy"))
    run(
        "export-backtest",
        "--bundle",
        results / "calculation",
        "--output",
        results / "run",
        "--strategy-package",
        results / "strategy",
        "--strategy-receipt",
        results / "strategy.receipt.json",
    )
    first = json.loads(run("publish", "--package", results / "run"))
    second = json.loads(run("publish", "--package", results / "run"))
    assert first == second and first["reference"]["kind"] == "run"
    assert strategy["reference"]["kind"] == "strategy"
    print("DoriBT, strategy/run export, exact lineage, registration and receipt recovery passed")


if __name__ == "__main__":
    main()
