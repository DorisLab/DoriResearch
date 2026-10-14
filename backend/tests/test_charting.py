import json
from pathlib import Path

import pytest
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
