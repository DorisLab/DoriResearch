"""Shared strict model for research requests."""

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
