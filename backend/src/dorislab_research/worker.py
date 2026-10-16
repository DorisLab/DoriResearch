"""Small optional adapter for the manual backtest panel, not a research task protocol."""

import importlib
import json
import sys
from pathlib import Path


def main() -> None:
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    module, name = request["callable"].rsplit(":", 1)
    output = Path(request["output"])
    result = getattr(importlib.import_module(module), name)(request["parameters"], output)
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
