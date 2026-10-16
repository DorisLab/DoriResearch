import json
import threading
from pathlib import Path
from typing import Any

import pytest

from dorislab_research import job_process
from dorislab_research.database import connect, migrate
from dorislab_research.examples import seed
from dorislab_research.jobs import cancel, job, start
from dorislab_research.library import Library
from dorislab_research.library_queries import listing


def test_cancel_wins_before_save_and_duplicate_request_starts_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migrate(tmp_path)
    library = Library(tmp_path)
    seed(library)
    strategy = listing(library, kind="strategy")[0]["reference"]
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    calls: list[str] = []

    def compute(identity: str, command: list[str], directory: Path, source: str | None) -> None:
        calls.append(identity)
        entered.set()
        assert release.wait(5)
        (directory / "result.json").write_text(json.dumps({"body": "must not save"}))

    original = job_process.forget

    def forget(identity: str) -> None:
        original(identity)
        finished.set()

    monkeypatch.setattr(job_process, "run", compute)
    monkeypatch.setattr(job_process, "forget", forget)
    args: dict[str, Any] = {"request_id": "same-request"}
    first = start(library, strategy, args)
    assert entered.wait(5)
    assert start(library, strategy, args)["id"] == first["id"]
    with pytest.raises(ValueError, match="其他回测"):
        start(library, strategy, {**args, "parameters": {"position": 0.8}})
    assert cancel(library, first["id"])["status"] == "cancelled"
    release.set()
    assert finished.wait(5)
    assert job(library, first["id"])["status"] == "cancelled"
    assert calls == [first["id"]]
    assert listing(library, kind="run") == []


def test_incompatible_schema_and_out_of_range_dates_are_explicit(tmp_path: Path) -> None:
    migrate(tmp_path)
    library = Library(tmp_path)
    seed(library)
    reference = listing(library, kind="strategy")[0]["reference"]
    for dates in ({"start": "2024-01-01"}, {"start": "2025-09-01", "end": "2025-01-01"}):
        with pytest.raises(ValueError):
            start(library, reference, dates)
    with connect(tmp_path) as db:
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
        db.execute("UPDATE alembic_version SET version_num='future' ")
    with pytest.raises(ValueError, match="不会自动降级"):
        library.content(reference)
