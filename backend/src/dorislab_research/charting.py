"""Shared Matplotlib theme and file export for research and DoriBT figures."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from cycler import cycler
from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.font_manager import fontManager
from matplotlib.ticker import MaxNLocator
from pydantic import BaseModel, ConfigDict, Field, model_validator

THEME: dict[str, Any] = json.loads(Path(__file__).with_name("chart_theme.json").read_text())
Role = Literal["strategy", "benchmark", "excess", "drawdown", "exposure"]


class Series(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str = Field(min_length=1)
    values: list[float | None]
    role: Role | None = None


class ChartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    kind: Literal["line", "scatter", "bar", "heatmap"] = "line"
    title: str
    x: list[float] | list[str]
    series: list[Series] = Field(min_length=1)
    x_label: str = ""
    y_label: str = ""

    @model_validator(mode="after")
    def aligned(self) -> "ChartRequest":
        if not self.x or any(len(s.values) != len(self.x) for s in self.series):
            raise ValueError("Each series must match the nonempty x axis")
        if self.kind == "scatter" and any(not isinstance(x, (int, float)) for x in self.x):
            raise ValueError("Scatter charts require numeric x values")
        return self


def color(role: Role | None, index: int = 0) -> str:
    return str(THEME[role] if role else THEME["palette"][index % len(THEME["palette"])])


@contextmanager
def chart_style() -> Iterator[None]:
    available = set(fontManager.get_font_names())
    fonts = [f for f in ("Microsoft YaHei", "Noto Sans CJK SC", "PingFang SC") if f in available]
    with rc_context(
        {
            "font.family": [*fonts, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "axes.prop_cycle": cycler(color=THEME["palette"]),
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    ):
        yield


def figure(request: ChartRequest) -> Figure:
    with chart_style():
        fig = Figure(figsize=(10, 5.6), layout="constrained")
        ax = fig.add_subplot()
        if request.kind == "heatmap":
            from matplotlib.colors import LinearSegmentedColormap

            cmap = LinearSegmentedColormap.from_list(
                "dorislab", [THEME["benchmark"], "#ffffff", THEME["strategy"]]
            )
            matrix = [[float("nan") if v is None else v for v in s.values] for s in request.series]
            artist = ax.imshow(matrix, aspect="auto", cmap=cmap)
            ax.set_xticks(range(len(request.x)), labels=[str(x) for x in request.x])
            ax.set_yticks(range(len(request.series)), labels=[s.name for s in request.series])
            fig.colorbar(artist, ax=ax)
        else:
            for index, series in enumerate(request.series):
                values = [float("nan") if v is None else v for v in series.values]
                series_color = color(series.role, index)
                if request.kind == "line":
                    ax.plot(
                        request.x,
                        values,
                        label=series.name,
                        color=series_color,
                        linestyle="--" if series.role == "benchmark" else "-",
                    )
                    if series.role == "drawdown":
                        ax.fill_between(request.x, values, 0, color=series_color, alpha=0.15)
                elif request.kind == "scatter":
                    ax.scatter(request.x, values, label=series.name, color=series_color)
                else:
                    width = 0.8 / len(request.series)
                    positions = [i - 0.4 + width * (index + 0.5) for i in range(len(request.x))]
                    ax.bar(positions, values, width=width, label=series.name, color=series_color)
                    ax.set_xticks(range(len(request.x)), labels=[str(x) for x in request.x])
            ax.legend(frameon=False)
            ax.grid(axis="y", alpha=0.18, color=THEME["neutral"])
        # 分类轴保留原有顺序与间隔，只减少标签，避免日期字符串逐点挤在一起。
        if request.kind in {"bar", "heatmap"} or (
            request.kind == "line" and isinstance(request.x[0], str)
        ):
            count = min(8, len(request.x))
            ticks = [round(i * (len(request.x) - 1) / max(1, count - 1)) for i in range(count)]
            ax.set_xticks(ticks, labels=[str(request.x[i]) for i in ticks])
        if request.kind == "bar" and all(
            value is None or float(value).is_integer()
            for series in request.series
            for value in series.values
        ):
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set(title=request.title, xlabel=request.x_label, ylabel=request.y_label)
        return fig


def save_figure(fig: Figure, output: Path, *, dpi: int = 160) -> Path:
    """Save a new PNG/SVG/PDF without opening a GUI or overwriting earlier evidence."""
    if output.suffix.lower() not in {".png", ".svg", ".pdf"}:
        raise ValueError("Chart output must be PNG, SVG or PDF")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        fig.savefig(stream, format=output.suffix[1:].lower(), dpi=dpi, facecolor="white")
    return output.resolve()


def export_chart(request: Path, output: Path) -> Path:
    return save_figure(figure(ChartRequest.model_validate_json(request.read_bytes())), output)
