"""Inspect the editable project without assuming the installed release is unchanged."""

import importlib.metadata
from pathlib import Path

FILES = (
    "AGENTS.md",
    "README.md",
    "docs/artifacts.md",
    "docs/metrics.md",
    "docs/data-and-execution.md",
    "docs/backtesting.md",
    "docs/host-compatibility.md",
    ".agents/skills/research-study/SKILL.md",
    ".agents/skills/strategy-evaluation/SKILL.md",
)


def inspect_project(root: Path) -> dict[str, object]:
    missing = [name for name in FILES if not (root / name).is_file()]
    return {
        "package": "dorislab-research",
        "version": importlib.metadata.version("dorislab-research"),
        "project": str(root.resolve()),
        "ready": not missing,
        "missing": missing,
        "profiles": ["dorislab.analysis.v1", "dorislab.etf-momentum.v1"],
        "host_registration": "requires-host-capability",
        "skill_discovery": "checked-by-codex-app-server-at-runtime",
    }
