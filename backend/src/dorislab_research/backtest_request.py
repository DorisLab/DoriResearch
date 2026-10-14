"""A deliberately bounded daily ETF research profile, owned by the editable project."""

from datetime import date
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)


class MomentumParameters(StrictModel):
    lookback: int = Field(default=20, ge=2, le=252)
    top_n: int = Field(default=2, ge=1, le=20)
    max_exposure: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)


class ExecutionAssumptions(StrictModel):
    # These are declared hypotheses, not an exchange-rule database.
    label: str = Field(min_length=1, max_length=1000)
    price_tick: Decimal = Field(gt=0)
    lot_size: int = Field(ge=1, le=10000)
    settlement_days: int = Field(ge=0, le=10)
    price_limit_ratio: Decimal = Field(gt=0, lt=1)
    commission: Decimal = Field(ge=0, le=1)
    minimum_commission: Decimal = Field(ge=0)
    stamp_duty_sell: Decimal = Field(ge=0, le=1)
    transfer_fee: Decimal = Field(ge=0, le=1)
    slippage_bps: Decimal = Field(ge=0, le=1000, decimal_places=2)
    max_participation: Decimal = Field(gt=0, le=1)


class BacktestRequest(StrictModel):
    profile: Literal["dorislab.etf-momentum.v1"] = "dorislab.etf-momentum.v1"
    title: str = Field(min_length=1, max_length=200)
    selection: str = Field(pattern=r"^[0-9a-f]{64}$")
    symbols: list[str] = Field(min_length=1, max_length=20)
    warmup_start: date
    start: date  # Initial valuation at this close; the first fill is a later session.
    end: date
    initial_cash: Decimal = Field(default=Decimal("100000"), gt=0)
    parameters: MomentumParameters = Field(default_factory=MomentumParameters)
    assumptions: ExecutionAssumptions
    benchmark: Literal["none", "cash_zero"] = "none"
    risk_free_rate: float = Field(default=0, gt=-1, le=1)
    target_return: float = Field(default=0, gt=-1, le=1)
    data_nature: Literal["real", "synthetic"] = "real"
    previous_run: str | None = None

    @model_validator(mode="after")
    def check_scope(self) -> Self:
        if not self.warmup_start < self.start < self.end:
            raise ValueError("Require warmup_start < initial valuation start < end")
        if len(set(self.symbols)) != len(self.symbols) or any(not s.strip() for s in self.symbols):
            raise ValueError("Symbols must be non-empty and unique")
        if self.parameters.top_n > len(self.symbols):
            raise ValueError("top_n exceeds the declared universe")
        return self
