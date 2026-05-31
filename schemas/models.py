from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StartupValidationRequest(BaseModel):
    startup_name: str = Field(..., min_length=2, max_length=80)
    idea_description: str = Field(..., min_length=20, max_length=3000)
    industry: str = Field(..., min_length=2, max_length=80)
    target_market: str = Field(..., min_length=2, max_length=160)
    geography: str = Field(..., min_length=2, max_length=80)
    team_size: int = Field(..., ge=1, le=100)
    timeline_months: int = Field(..., ge=1, le=60)
    unique_value_prop: str | None = Field(default=None, max_length=500)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    model: str
    dependencies: dict[str, bool]
    fallback_enabled: bool


class ValidationResponse(BaseModel):
    execution_mode: str
    execution_time_s: float
    specialist_reports: dict[str, Any]
    conflicts_detected: list[str]
    final_evaluation: dict[str, Any]

