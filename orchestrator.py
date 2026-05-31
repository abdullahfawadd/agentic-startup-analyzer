from __future__ import annotations

import time
from typing import Any

from agents.market_research import MarketResearchAgent
from agents.risk_assessment import RiskAssessmentAgent
from agents.viability_scorer import ViabilityScorerAgent
from core.config import Settings, get_settings
from core.llm import GroqLLM
from schemas.models import StartupValidationRequest


class StartupValidationOrchestrator:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.llm = GroqLLM(self.settings)
        self.market_agent = MarketResearchAgent(self.settings, self.llm)
        self.risk_agent = RiskAssessmentAgent(self.llm)
        self.viability_agent = ViabilityScorerAgent(self.llm)

    def validate(self, request: StartupValidationRequest) -> dict[str, Any]:
        started = time.perf_counter()
        payload = request.model_dump()

        reports = {
            "market_research": self._safe_agent("market_research", self.market_agent.analyze, self._market_payload(payload)),
            "risk_swot": self._safe_agent("risk_swot", self.risk_agent.analyze, self._risk_payload(payload)),
            "viability_scorer": self._safe_agent("viability_scorer", self.viability_agent.analyze, self._viability_payload(payload)),
        }
        conflicts = self.detect_conflicts(reports)
        final = self._synthesize(payload, reports, conflicts)
        return {
            "execution_mode": "sequential",
            "execution_time_s": round(time.perf_counter() - started, 2),
            "specialist_reports": reports,
            "conflicts_detected": conflicts,
            "final_evaluation": final,
        }

    def _safe_agent(self, name: str, fn, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return fn(payload)
        except Exception as exc:
            return {
                "status": "failed",
                "executive_summary": f"{name} could not complete. The orchestrator continued with fallback scoring.",
                "error": type(exc).__name__,
            }

    def _market_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "startup_name": payload["startup_name"],
            "idea_description": payload["idea_description"],
            "industry": payload["industry"],
            "target_market": payload["target_market"],
            "geography": payload["geography"],
        }

    def _risk_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "startup_name": payload["startup_name"],
            "idea_description": payload["idea_description"],
            "industry": payload["industry"],
            "target_market": payload["target_market"],
        }

    def _viability_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "startup_name": payload["startup_name"],
            "idea_description": payload["idea_description"],
            "industry": payload["industry"],
            "target_market": payload["target_market"],
            "geography": payload["geography"],
            "team_size": payload["team_size"],
            "timeline_months": payload["timeline_months"],
            "unique_value_prop": payload.get("unique_value_prop"),
        }

    def detect_conflicts(self, reports: dict[str, Any]) -> list[str]:
        conflicts: list[str] = []
        market = reports.get("market_research", {})
        risk = reports.get("risk_swot", {})
        viability = reports.get("viability_scorer", {})

        market_text = " ".join(
            [
                str(market.get("market_analysis", "")),
                str(market.get("estimated_market_size", "")),
                " ".join(market.get("key_trends", []) if isinstance(market.get("key_trends"), list) else []),
            ]
        ).lower()
        viability_score = float(viability.get("viability_score") or 0)
        competition_score = float(viability.get("competition_score") or 10)
        risk_level = str(risk.get("risk_level", "")).lower()

        if any(token in market_text for token in ["large", "rapid", "strong", "$", "growing"]) and viability_score < 6:
            conflicts.append("Market research shows a large opportunity, but the viability score is below the investable threshold.")
        if risk_level == "low" and competition_score < 5.8:
            conflicts.append("SWOT indicates low risk, but the Tool Use scorer found intense competition pressure.")
        if competition_score < 6 and viability_score >= 7:
            conflicts.append("Overall viability is promising, but differentiation risk remains a major execution dependency.")
        return conflicts

    def _synthesize(self, payload: dict[str, Any], reports: dict[str, Any], conflicts: list[str]) -> dict[str, Any]:
        fallback = self._fallback_synthesis(payload, reports, conflicts)
        if not self.llm.available:
            return fallback

        system = (
            "You are an investor-style startup evaluation orchestrator. Return strict JSON only. "
            "Use the specialist reports, acknowledge conflicts, and be decisive."
        )
        user = f"""
Startup input:
{payload}

Specialist reports:
{reports}

Conflicts:
{conflicts}

Return JSON:
{{
  "verdict": "PROMISING|VIABLE WITH CAUTION|NEEDS VALIDATION|HIGH RISK",
  "overall_score": 0.0,
  "top_strengths": [],
  "top_concerns": [],
  "recommendations": [],
  "summary": ""
}}
"""
        result = self.llm.complete_json(system, user, fallback=fallback, max_tokens=1200)
        return {**fallback, **result}

    def _fallback_synthesis(self, payload: dict[str, Any], reports: dict[str, Any], conflicts: list[str]) -> dict[str, Any]:
        viability = reports.get("viability_scorer", {})
        risk = reports.get("risk_swot", {})
        score = float(viability.get("viability_score") or 6.4)
        risk_level = str(risk.get("risk_level", "Medium")).lower()
        if risk_level == "high":
            score -= 0.7
        elif risk_level == "low":
            score += 0.3
        score = round(max(1, min(10, score)), 1)
        verdict = "PROMISING" if score >= 7.4 else "VIABLE WITH CAUTION" if score >= 6.5 else "NEEDS VALIDATION" if score >= 5.3 else "HIGH RISK"
        return {
            "verdict": verdict,
            "overall_score": score,
            "top_strengths": [
                "Clear target problem with measurable customer pain",
                "Can launch in a narrow segment before expanding",
                "Agentic analysis creates a strong course-demo narrative",
            ],
            "top_concerns": [
                "Differentiation must be proven against fast-moving competitors",
                "Early liquidity and retention are critical",
                "Operational execution may be harder than the product prototype",
            ],
            "recommendations": [
                "Start with one city and one tightly defined customer segment",
                "Run concierge pilots before automating the full marketplace",
                "Track savings, repeat usage, and acquisition cost from day one",
            ],
            "summary": f"{payload['startup_name']} is {verdict.lower()} with an overall score of {score}/10. The opportunity is credible, but the launch should stay narrow until demand, margins, and retention are validated.",
            "conflict_count": len(conflicts),
        }

