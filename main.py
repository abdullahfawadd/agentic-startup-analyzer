from __future__ import annotations

from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from core.config import get_settings
from orchestrator import StartupValidationOrchestrator
from schemas.models import (
    FollowUpRequest,
    FollowUpResponse,
    HealthResponse,
    PitchDeckRequest,
    PitchDeckResponse,
    StartupValidationRequest,
    ValidationResponse,
)


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Agentic startup idea validation using ReAct, Reflection, Tool Use, and orchestration.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(Path("frontend/index.html"))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    dependencies = {"groq": settings.groq_ready, "tavily": settings.tavily_ready}
    ready = all(dependencies.values())
    return HealthResponse(
        status="ok" if ready else "degraded",
        app=settings.app_name,
        model=settings.groq_model,
        dependencies=dependencies,
        fallback_enabled=settings.allow_demo_fallback,
    )


@app.post("/validate", response_model=ValidationResponse)
def validate_startup(request: StartupValidationRequest) -> dict:
    orchestrator = StartupValidationOrchestrator(settings)
    return orchestrator.validate(request)


@app.post("/n8n/validate", response_model=ValidationResponse)
def validate_with_n8n(request: StartupValidationRequest) -> dict:
    if not settings.n8n_webhook_url:
        raise HTTPException(status_code=503, detail="N8N_WEBHOOK_URL is not configured")

    payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
    try:
        response = requests.post(
            settings.n8n_webhook_url,
            json=payload,
            timeout=max(settings.api_timeout_seconds, 120),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"n8n webhook request failed: {exc}") from exc

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="n8n webhook did not return JSON") from exc


@app.post("/follow-up", response_model=FollowUpResponse)
def follow_up(request: FollowUpRequest) -> dict:
    orchestrator = StartupValidationOrchestrator(settings)
    return orchestrator.answer_follow_up(
        question=request.question,
        report=request.report,
        history=request.history,
    )


@app.post("/pitch-deck", response_model=PitchDeckResponse)
def pitch_deck(request: PitchDeckRequest) -> dict:
    orchestrator = StartupValidationOrchestrator(settings)
    return orchestrator.generate_pitch_deck(
        report=request.report,
        startup_name=request.startup_name,
    )
