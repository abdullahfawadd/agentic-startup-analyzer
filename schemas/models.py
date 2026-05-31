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


class FollowUpRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=800)
    report: dict[str, Any]
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)


class FollowUpResponse(BaseModel):
    answer: str
    suggested_questions: list[str]


class PitchDeckRequest(BaseModel):
    report: dict[str, Any]
    startup_name: str | None = Field(default=None, max_length=80)


class PitchDeckResponse(BaseModel):
    title: str
    slides: list[dict[str, Any]]
