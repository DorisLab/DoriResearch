import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image
from pydantic import ValidationError

from dorislab_research.charting import ChartRequest, color, export_chart, figure, save_figure


@pytest.mark.parametrize("kind", ["line", "scatter", "bar", "heatmap"])
def test_chart_exports_actual_images_with_shared_roles(tmp_path: Path, kind: str) -> None:
    request = tmp_path / "chart.json"
    request.write_text(
        json.dumps(
            {
                "title": "策略与基准",
                "kind": kind,
                "x": [1, 2, 3],
                "series": [
                    {"name": "策略", "role": "strategy", "values": [1, 1.1, 1.2]},
                    {"name": "基准", "role": "benchmark", "values": [1, None, 1.1]},
                ],
            }
        ),
        encoding="utf-8",
    )
    path = export_chart(request, tmp_path / "cover.png")
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.width >= 1000 and image.height >= 500
        assert len(image.getcolors(image.width * image.height) or []) > 100
    assert path.stat().st_size < 1024 * 1024
    with pytest.raises(FileExistsError):
        export_chart(request, path)
    fig = figure(ChartRequest.model_validate_json(request.read_bytes()))
    if kind == "line":
        assert [line.get_color() for line in fig.axes[0].lines] == [
            color("strategy"),
            color("benchmark"),
        ]
        assert color("strategy") == "#c83932" and color("benchmark") == "#477bb5"
    for extension in ["svg", "pdf"]:
        saved = save_figure(fig, tmp_path / f"chart.{extension}")
        assert saved.stat().st_size > 1000


def test_invalid_alignment_and_nonfinite_values_are_rejected() -> None:
    for values in [[1], [1, float("nan")]]:
        with pytest.raises(ValidationError):
            ChartRequest.model_validate(
                {"title": "x", "x": [1, 2], "series": [{"name": "a", "values": values}]}
            )


def test_dense_dates_render_without_adjacent_label_overlap(tmp_path: Path) -> None:
    chart = figure(
        ChartRequest.model_validate(
            {
                "title": "60日合成净值",
                "x": [str(date(2026, 8, 1) + timedelta(days=i)) for i in range(60)],
                "series": [{"name": "策略", "values": [1 + i / 100 for i in range(60)]}],
            }
        )
    )
    canvas: Any = FigureCanvasAgg(chart)
    canvas.draw()
    bounds = [
        label.get_window_extent(canvas.get_renderer()) for label in chart.axes[0].get_xticklabels()
    ]
    assert len(bounds) <= 8
    assert not any(a.overlaps(b) for a, b in zip(bounds, bounds[1:], strict=False))
    save_figure(chart, tmp_path / "dates.png")


def test_integer_bars_and_drawdown_have_readable_scales_and_style() -> None:
    bars = figure(
        ChartRequest.model_validate(
            {
                "title": "次数",
                "kind": "bar",
                "x": ["甲", "乙", "丙"],
                "series": [{"name": "事件", "values": [1, 2, 3]}],
            }
        )
    )
    canvas: Any = FigureCanvasAgg(bars)
    canvas.draw()
    assert bars.axes[0].get_ylim()[0] == 0
    assert all(float(tick).is_integer() for tick in bars.axes[0].get_yticks())
    drawdown = figure(
        ChartRequest.model_validate(
            {
                "title": "回撤",
                "x": [1, 2, 3],
                "series": [{"name": "回撤", "role": "drawdown", "values": [0, -0.2, -0.1]}],
            }
        )
    )
    assert drawdown.axes[0].lines[0].get_color() == "#2f8a62"
    assert len(drawdown.axes[0].collections) == 1
