"""First-install examples are ordinary editable content and are never resurrected."""

import json
import tempfile
from pathlib import Path

from .database import connect
from .example_calculation import backtest
from .example_content import BACKTEST, STRATEGY_BODY, STUDY_BODY
from .library import Library


def seed(library: Library) -> None:
    with connect(library.root) as db:
        if db.execute("SELECT value FROM settings WHERE key='examples.v1'").fetchone():
            return
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        result = backtest({"cost_bps": 10, "position": 0.2}, output)
        study = seed_item(
            library,
            "sample-study-v1",
            kind="study",
            title="十次赢七次，为什么账户还是亏的？",
            summary="用一组可重复的模拟交易，拆开胜率、单次盈亏和交易费用，看看高胜率的盲区。",
            body=STUDY_BODY,
            files={name: output / name for name in result["files"]},
            origin="example",
            data_nature="synthetic",
        )
        config = BACKTEST
        (output / "backtest.json").write_text(
            json.dumps(config, ensure_ascii=False), encoding="utf-8"
        )
        seed_item(
            library,
            "sample-strategy-v1",
            kind="strategy",
            title="高胜率、小盈利与大亏损：仓位实验",
            summary="固定交易机会，只改变仓位和成本。试着降低费用，看看它能否改变结果。",
            body=STRATEGY_BODY,
            references=[study],
            config=config,
            files={"backtest.json": output / "backtest.json"},
            origin="example",
            data_nature="synthetic",
        )
    with connect(library.root) as db:
        db.execute("INSERT INTO settings VALUES ('examples.v1','1')")


def seed_item(library: Library, identity: str, **kwargs: object) -> dict[str, str]:
    from typing import Any, cast
    from uuid import NAMESPACE_URL, uuid5

    identity = str(uuid5(NAMESPACE_URL, f"https://github.com/DorisLab/DoriResearch/{identity}"))
    with connect(library.root) as db:
        existing = db.execute(
            "SELECT kind,revision FROM entries WHERE id=?", (identity,)
        ).fetchone()
    if existing:
        return {"kind": existing["kind"], "id": identity, "version": str(existing["revision"])}
    return library.save(id=identity, **cast(Any, kwargs))
