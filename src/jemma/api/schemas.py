from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SoloBenchmarkRequest(BaseModel):
    name: str = Field(default="api-solo-benchmark")
    models: list[str]
    dataset_path: str
    repetitions: int = Field(default=1, ge=1)
    warmup_runs: int = Field(default=0, ge=0)
    visibility: Literal["local", "public"] = "local"
    options: dict[str, Any] = Field(default_factory=dict)


class PairwiseBenchmarkRequest(BaseModel):
    name: str = Field(default="api-pairwise-benchmark")
    left_model: str
    right_model: str
    dataset_path: str
    repetitions: int = Field(default=1, ge=1)
    warmup_runs: int = Field(default=0, ge=0)
    visibility: Literal["local", "public"] = "local"
    options: dict[str, Any] = Field(default_factory=dict)


class StressBenchmarkRequest(BaseModel):
    name: str = Field(default="api-stress-benchmark")
    models: list[str]
    standard_dataset_path: str
    reasoning_dataset_path: str
    repetitions: int = Field(default=1, ge=1)
    warmup_runs: int = Field(default=0, ge=0)
    visibility: Literal["local", "public"] = "local"
    options: dict[str, Any] = Field(default_factory=dict)

