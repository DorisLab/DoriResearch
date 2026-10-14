"""Small, traceable analysis profile; runs inside the Agent's native terminal command."""

import csv
import io
import math
import statistics
from datetime import date
from typing import Literal, Self

from pydantic import Field, model_validator

from .models import Model


class AnalysisRequest(Model):
    schema_name: Literal["dorislab.analysis.request.v1"] = "dorislab.analysis.request.v1"
    title: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=4000)
    input_file: str = Field(min_length=1)
    source_label: str = Field(min_length=1, max_length=1000)
    data_nature: Literal["real", "synthetic", "mixed"]
    unit: str = Field(min_length=1, max_length=100)
    date_column: str = "date"
    value_column: str = "value"
    missing: Literal["reject", "drop"] = "reject"
    start: date | None = None
    end: date | None = None
    previous_run: str | None = None

    @model_validator(mode="after")
    def range_valid(self) -> Self:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must not be after end")
        if self.date_column == self.value_column:
            raise ValueError("date and value columns must differ")
        return self


class AnalysisResult(Model):
    schema_name: Literal["dorislab.analysis.v1"] = "dorislab.analysis.v1"
    start: date
    end: date
    observations: int = Field(ge=1)
    missing_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    unit: str
    first: float
    last: float
    minimum: float
    maximum: float
    mean: float
    sample_std: float | None
    change: float
    relative_change: float | None
    relative_change_reason: str | None
    method: Literal["descriptive-statistics.v1"] = "descriptive-statistics.v1"


def observations(
    data: bytes, request: AnalysisRequest
) -> tuple[list[tuple[date, float]], int, int]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    columns = reader.fieldnames or []
    if len(set(columns)) != len(columns) or not {request.date_column, request.value_column} <= set(
        columns
    ):
        raise ValueError("CSV must have unique headers including the requested columns")
    selected: list[tuple[date, float]] = []
    seen: set[date] = set()
    missing = excluded = 0
    for index, row in enumerate(reader):
        if index >= 200_000:
            raise ValueError("Analysis input exceeds 200000 rows")
        day = date.fromisoformat(row[request.date_column])
        if day in seen:
            raise ValueError("Duplicate dates require an explicit aggregation method")
        seen.add(day)
        if (request.start and day < request.start) or (request.end and day > request.end):
            excluded += 1
            continue
        raw = row[request.value_column]
        if raw is None or not raw.strip():
            if request.missing == "reject":
                raise ValueError("Missing value; choose and document a missing-data policy")
            missing += 1
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("Non-finite input value")
        selected.append((day, value))
    if not selected:
        raise ValueError("No observations in the requested scope")
    return sorted(selected), missing, excluded


def calculate(data: bytes, request: AnalysisRequest) -> AnalysisResult:
    rows, missing, excluded = observations(data, request)
    values = [value for _, value in rows]
    first, last = values[0], values[-1]
    return AnalysisResult(
        start=rows[0][0],
        end=rows[-1][0],
        observations=len(values),
        missing_count=missing,
        excluded_count=excluded,
        unit=request.unit,
        first=first,
        last=last,
        minimum=min(values),
        maximum=max(values),
        mean=statistics.mean(values),
        sample_std=statistics.stdev(values) if len(values) > 1 else None,
        change=last - first,
        relative_change=(last / first - 1) if first > 0 else None,
        relative_change_reason=None if first > 0 else "初值非正，比例变化不适用",
    )


def report(request: AnalysisRequest, result: AnalysisResult) -> str:
    nature = {"real": "真实材料（按请求声明）", "synthetic": "合成输入", "mixed": "混合输入"}
    return (
        f"# {request.title}\n\n{request.question}\n\n"
        f"来源：{request.source_label}；{nature[request.data_nature]}。\n\n"
        f"实际范围：{result.start}—{result.end}；{result.observations} 个观察值；"
        f"单位：{result.unit}。\n\n"
        f"首值 {result.first:g}，末值 {result.last:g}，变化 {result.change:g}；"
        f"均值 {result.mean:g}，最小值 {result.minimum:g}，最大值 {result.maximum:g}。\n\n"
        f"方法：{result.method}；范围外 {result.excluded_count} 行，"
        f"缺失剔除 {result.missing_count} 行。\n\n"
        "本结果只提供描述统计，不自动推断因果、资金流入或策略收益。输入真实性与研究解释仍需核对。\n\n"
        "[完整结果](result.json) · [请求](request.json) · "
        "[输入快照](input.csv) · [运行记录](run.json)\n"
    )
