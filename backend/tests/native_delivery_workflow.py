"""Invoked by the existing Rust/App Server publication fixture; no model or real account data."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
work = root / "research" / "results" / sys.argv[2]
assert work.resolve().is_relative_to(root) and work != root
project = work / "project"
bootstrap = root / "fixture project" / "run.py"
shutil.copytree(bootstrap.parent, project)
materials = work / "materials"
materials.mkdir()
(materials / "compute.py").write_text(
    "import json,sys\nfrom pathlib import Path\n"
    "parameters=json.loads(Path(sys.argv[1]).read_text())\n"
    "values=json.loads(Path(parameters['input']).read_text())\n"
    "Path(sys.argv[2]).write_text(str(sum(values)))\n",
    encoding="utf-8",
)
(materials / "parameters.json").write_text('{"input":"input.json"}')
(materials / "input.json").write_text("[1,2]")
shutil.copyfile(project / "backend" / "uv.lock", materials / "uv.lock")
(materials / "report.md").write_text("# Portable fixture\nSum: 3.\n", encoding="utf-8")
(materials / "request.json").write_text(
    json.dumps(
        {
            "title": "可接续研究验收",
            "summary": "Isolated save and prepare fixture.",
            "data_nature": "synthetic",
            "files": ["report.md", "compute.py", "parameters.json", "input.json", "uv.lock"],
            "execution": {
                "entrypoint": "compute.py",
                "parameters": ["parameters.json"],
                "environment": ["uv.lock"],
                "data": ["input.json"],
                "evidence": [],
                "instructions": "From materials: python compute.py parameters.json <new output>.",
            },
        }
    ),
    encoding="utf-8",
)


def run(launcher: Path, *arguments: str | Path, cwd: Path = root) -> str:
    result = subprocess.run(
        [sys.executable, str(launcher), *map(str, arguments)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout


run(
    project / "run.py",
    "python",
    materials / "compute.py",
    "parameters.json",
    "original.txt",
    cwd=materials,
)
assert (materials / "original.txt").read_text() == "3"
arguments: list[str | Path] = [
    "save-study",
    "--request",
    materials / "request.json",
    "--output",
    work / "export",
    "--project",
    project,
]
first = json.loads(run(bootstrap, *arguments))
assert json.loads(run(bootstrap, *arguments)) == first
receipt = root / "delivery.receipt.json"
receipt.write_text(json.dumps(first), encoding="utf-8")
saved_launcher = (project / "run.py").read_bytes()
shutil.rmtree(work)
bootstrap.write_bytes(bootstrap.read_bytes() + b"\n# Account project changed after saving.\n")
prepared = json.loads(run(bootstrap, "prepare-publication", "--receipt", receipt))
assert prepared["reproduction_status"] == "not_verified"
restored = Path(prepared["project"])
copied = Path(prepared["materials"])
assert (restored / "run.py").read_bytes() == saved_launcher
run(
    restored / "run.py",
    "python",
    copied / "compute.py",
    "parameters.json",
    "verified.txt",
    cwd=copied,
)
assert (copied / "verified.txt").read_text() == "3"
print("Save, receipt retry, original directory removal and restored execution passed.")
