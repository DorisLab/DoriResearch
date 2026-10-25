"""DoriResearch owns this database. Only explicit activation runs migrations."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, create_engine


def data_root(root: Path | None = None) -> Path:
    value = root or os.environ.get("DORIRESEARCH_DATA")
    if not value:
        raise ValueError("DORIRESEARCH_DATA 未设置，请先准备研究环境")
    return Path(value).resolve()


def migrate(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    engine = create_engine(URL.create("sqlite", database=str(root / "library.sqlite")))
    try:
        with engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
    finally:
        engine.dispose()


@contextmanager
def connect(root: Path) -> Iterator[sqlite3.Connection]:
    # mode=rw prevents an obsolete/misconfigured workspace from creating a new empty database.
    db = sqlite3.connect((root / "library.sqlite").as_uri() + "?mode=rw", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    try:
        actual = {row[0] for row in db.execute("SELECT version_num FROM alembic_version")}
        if actual != schema_heads():
            raise ValueError(
                "此工作区与研究数据库版本不兼容，请整合当前工程后接续；不会自动降级数据库"
            )
    except Exception:
        db.close()
        raise
    try:
        with db:
            yield db
    finally:
        db.close()


@lru_cache(maxsize=1)
def schema_heads() -> set[str]:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    return set(ScriptDirectory.from_config(cfg).get_heads())


def writable(root: Path) -> None:
    if (root / "maintenance.json").exists():
        raise ValueError("工程正在升级，请等待启用完成后重新保存")
