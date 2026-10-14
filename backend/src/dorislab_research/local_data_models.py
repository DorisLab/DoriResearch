"""Host-owned discovery envelope; dataset semantics remain in the supplied specification."""

from datetime import date
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DateRange(BaseModel):
    start: date
    end: date


class DataFile(BaseModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0, le=64 * 1024 * 1024)
    partition: str
    dates: DateRange | None = None


class Dataset(BaseModel):
    view: dict[str, Any]
    spec: dict[str, Any]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    files: list[DataFile]


class PlanRequest(BaseModel):
    release_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    dates: DateRange
    dataset_ids: list[str]


class Plan(BaseModel):
    request: PlanRequest
    datasets: list[Dataset]


class Selection(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan: Plan


class LocalCatalog(BaseModel):
    schema_name: Literal["dorislab.local-data.v1"] = Field(alias="schema")
    objects_root: Path
    selections: list[Selection]
    agent_run_id: str
    created_at_ms: int

    @model_validator(mode="after")
    def absolute_root(self) -> Self:
        if not self.objects_root.is_absolute():
            raise ValueError("Host data root must be absolute")
        if len({item.id for item in self.selections}) != len(self.selections):
            raise ValueError("Duplicate installed selection")
        return self


class DataQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selection: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset: str
    columns: list[str] = Field(min_length=1, max_length=100)
    symbols: list[str] = Field(default_factory=list, max_length=10000)
    start: date | None = None
    end: date | None = None
    max_rows: int = Field(default=100000, ge=1, le=200000)

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if (self.start is None) != (self.end is None):
            raise ValueError("Supply both start and end")
        if self.start and self.end and self.start > self.end:
            raise ValueError("Start must not exceed end")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Duplicate requested column")
        return self
