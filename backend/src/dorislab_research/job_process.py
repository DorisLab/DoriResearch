"""Subprocess ownership for manual runs; a failed reader never reports success."""

import os
import subprocess
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

_lock = threading.RLock()
_children: dict[str, subprocess.Popen[bytes]] = {}
_cancelled: set[str] = set()


def run(identity: str, command: list[str], directory: Path, source: str | None) -> None:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with (directory / "execution.log").open("wb") as log:
        with _lock:
            if identity in _cancelled:
                raise ValueError("回测已取消")
            child = subprocess.Popen(
                command,
                cwd=source,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                creationflags=flags,
                env={
                    key: value for key, value in os.environ.items() if key != "DORIRESEARCH_TOKEN"
                },
            )
            _children[identity] = child
        try:
            code = child.wait()
            with _lock:
                if identity in _cancelled:
                    raise ValueError("回测已取消")
            if code:
                detail = (directory / "execution.log").read_text(
                    encoding="utf-8", errors="replace"
                )[-6000:]
                raise ValueError(detail or f"回测程序退出（{code}）")
        finally:
            with _lock:
                _children.pop(identity, None)


def cancel(identity: str) -> None:
    with _lock:
        _cancelled.add(identity)
        child = _children.get(identity)
        if child and child.poll() is None:
            child.terminate()


@contextmanager
def completion_lock() -> Iterator[None]:
    with _lock:
        yield


def finish(identity: str, save: Callable[[], None]) -> None:
    # Cancel and the final save share the same lock order: process, then database.
    with _lock:
        if identity in _cancelled:
            raise ValueError("回测已取消")
        save()


def forget(identity: str) -> None:
    with _lock:
        _cancelled.discard(identity)


def stop_all() -> None:
    with _lock:
        for identity in list(_children):
            cancel(identity)
