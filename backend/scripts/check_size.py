"""Enforce the repository's file and function limits for standalone server checks."""

import ast
import io
import sys
import tokenize
from pathlib import Path


def violations(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    errors = []
    if len(source.splitlines()) > 400:
        errors.append(f"{path}: more than 400 physical lines")
    ignored = {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
    code_lines: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type not in ignored:
            code_lines.update(range(token.start[0], token.end[0] + 1))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            length = len(code_lines.intersection(range(node.lineno, (node.end_lineno or 0) + 1)))
            if length > 80:
                errors.append(f"{path}:{node.lineno}: {node.name} exceeds 80 code lines")
    return errors


def main() -> int:
    errors = [
        error
        for root in ("src", "tests", "scripts")
        for path in Path(root).rglob("*.py")
        for error in violations(path)
    ]
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
