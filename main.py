from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from core.config import get_settings
from orchestrator import StartupValidationOrchestrator
from schemas.models import HealthResponse, StartupValidationRequest, ValidationResponse


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

