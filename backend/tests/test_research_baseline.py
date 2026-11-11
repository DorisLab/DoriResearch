"""Research baseline executes table statistics and preserves Parquet values."""

import importlib
from pathlib import Path

import numpy as np
import pyarrow as pa


def test_baseline_reads_parquet_and_runs_rank_statistics(tmp_path: Path) -> None:
    # Dynamic imports keep optional typing stubs out of the runtime dependency set.
    pandas = importlib.import_module("pandas")
    pq = importlib.import_module("pyarrow.parquet")
    stats = importlib.import_module("scipy.stats")
    path = tmp_path / "observations.parquet"
    pq.write_table(pa.table({"signal": [3.0, 1.0, 4.0, 2.0], "return": [0.3, 0.1, 0.4, 0.2]}), path)
    frame = pandas.read_parquet(path)
    result = stats.spearmanr(frame["signal"], frame["return"])
    assert np.isclose(result.statistic, 1.0)
    assert result.pvalue < 0.01
    assert frame.sort_values("signal")["return"].tolist() == [0.1, 0.2, 0.3, 0.4]
