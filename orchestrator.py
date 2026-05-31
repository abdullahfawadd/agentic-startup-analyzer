from __future__ import annotations

import time
from typing import Any

from agents.market_research import MarketResearchAgent
from agents.risk_assessment import RiskAssessmentAgent
from agents.viability_scorer import ViabilityScorerAgent
from core.config import Settings, get_settings
from core.json_utils import ensure_list
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

    def answer_follow_up(
        self,
        *,
        question: str,
        report: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        fallback = self._fallback_follow_up(question, report)
        if not self.llm.available:
            return fallback

        system = (
            "You are a concise startup advisor continuing a validation chat. "
            "Answer the user's follow-up using the provided report. Return strict JSON only."
        )
        user = f"""
Question:
{question}

Prior chat:
{history or []}

Validation report:
{report}

Return JSON:
{{
  "answer": "direct answer in 2-4 short paragraphs",
  "suggested_questions": ["next question 1", "next question 2", "next question 3"]
}}
"""
        result = self.llm.complete_json(system, user, fallback=fallback, max_tokens=750)
        merged = {**fallback, **result}
        return {
            "answer": str(merged.get("answer") or fallback["answer"]),
            "suggested_questions": [str(item) for item in ensure_list(merged.get("suggested_questions"), fallback["suggested_questions"])[:4]],
        }

    def generate_pitch_deck(self, *, report: dict[str, Any], startup_name: str | None = None) -> dict[str, Any]:
        fallback = self._fallback_pitch_deck(report, startup_name)
        if not self.llm.available:
            return fallback

        system = (
            "You are a startup pitch deck strategist. Create a concise investor deck outline "
            "from the validation report. Return strict JSON only."
        )
        user = f"""
Startup name: {startup_name or "Startup"}

Validation report:
{report}

Return JSON:
{{
  "title": "Deck title",
  "slides": [
    {{"title": "Slide title", "bullets": ["bullet 1", "bullet 2"], "speaker_note": "short note"}}
  ]
}}

Create 8-10 slides: problem, customer, solution, market, product, traction/validation plan,
business model, go-to-market, risks, ask/next steps.
"""
        result = self.llm.complete_json(system, user, fallback=fallback, max_tokens=1300)
        merged = {**fallback, **result}
        slides = []
        for item in ensure_list(merged.get("slides"), fallback["slides"])[:10]:
            if isinstance(item, dict):
                slides.append(
                    {
                        "title": str(item.get("title") or "Slide"),
                        "bullets": [str(bullet) for bullet in ensure_list(item.get("bullets"), [])[:5]],
                        "speaker_note": str(item.get("speaker_note") or ""),
                    }
                )
        return {"title": str(merged.get("title") or fallback["title"]), "slides": slides or fallback["slides"]}

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
  "validation_experiments": [],
  "mvp_blueprint": [],
  "marketing_plan": [],
  "technical_structure": [],
  "follow_up_questions": [],
  "summary": ""
}}
"""
        result = self.llm.complete_json(system, user, fallback=fallback, max_tokens=850)
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
            "validation_experiments": [
                "Interview 15 target buyers and measure the exact saving threshold that changes behavior",
                "Run a concierge group-buying pilot with 30-50 orders before building automation",
                "Compare repeat purchase rate between household buyers and small retailers",
            ],
            "mvp_blueprint": [
                "Landing page with city/category selection and waitlist capture",
                "Admin dashboard for supplier offers, pooled orders, and delivery status",
                "Basic AI matching layer that clusters demand by product, location, and price target",
            ],
            "marketing_plan": [
                "Launch with one high-frequency category and publish real savings examples",
                "Recruit early users through local retailer partnerships and neighborhood groups",
                "Use referral credits only after repeat purchase behavior is proven",
            ],
            "technical_structure": [
                "FastAPI backend for orchestration, validation, and report generation",
                "Agent layer split into market research, risk reflection, and viability scoring",
                "n8n workflow mirror for visual automation and course demonstration",
            ],
            "follow_up_questions": [
                "Which city and product category should the first pilot focus on?",
                "What minimum discount makes buyers wait for pooled delivery?",
                "Who owns supplier reliability and customer support during the pilot?",
            ],
            "summary": f"{payload['startup_name']} is {verdict.lower()} with an overall score of {score}/10. The opportunity is credible, but the launch should stay narrow until demand, margins, and retention are validated.",
            "conflict_count": len(conflicts),
        }

    def _fallback_follow_up(self, question: str, report: dict[str, Any]) -> dict[str, Any]:
        final = report.get("final_evaluation", {}) if isinstance(report, dict) else {}
        recommendations = final.get("recommendations") or [
            "Start with a narrow pilot",
            "Measure repeat usage",
            "Validate unit economics",
        ]
        answer = (
            f"Based on the report, the best answer is to keep the next step narrow and measurable. "
            f"For: {question}\n\n"
            f"I would prioritize {recommendations[0]}. Then compare the result against customer acquisition cost, "
            "repeat usage, and operational reliability before expanding the scope."
        )
        return {
            "answer": answer,
            "suggested_questions": [
                "What should the first 30-day pilot measure?",
                "Which customer segment should launch first?",
                "What would make this idea non-viable?",
            ],
        }

    def _fallback_pitch_deck(self, report: dict[str, Any], startup_name: str | None) -> dict[str, Any]:
        final = report.get("final_evaluation", {}) if isinstance(report, dict) else {}
        name = startup_name or "Startup"
        return {
            "title": f"{name} Investor Pitch Deck Outline",
            "slides": [
                {"title": "Problem", "bullets": final.get("top_concerns", ["Customers face a painful, measurable workflow problem"])[:3], "speaker_note": "Open with the customer pain and why now."},
                {"title": "Target Customer", "bullets": ["Define the first narrow segment", "Show who pays or repeats", "Explain the buying trigger"], "speaker_note": "Avoid a broad everyone-market."},
                {"title": "Solution", "bullets": final.get("top_strengths", ["Focused AI-enabled workflow", "Clear launch wedge"])[:3], "speaker_note": "Connect the product directly to the pain."},
                {"title": "Market Opportunity", "bullets": ["Show TAM/SAM/SOM", "Use live market signals", "Name adjacent competitors"], "speaker_note": "Keep market claims tied to sources."},
                {"title": "MVP", "bullets": final.get("mvp_blueprint", ["Landing page", "Admin dashboard", "Concierge pilot"])[:4], "speaker_note": "Explain what will be built first."},
                {"title": "Validation Plan", "bullets": final.get("validation_experiments", ["Run pilot", "Measure retention", "Track unit economics"])[:4], "speaker_note": "This is strongest for a course demo."},
                {"title": "Go-To-Market", "bullets": final.get("marketing_plan", ["Launch one city", "Partner locally", "Publish proof"])[:4], "speaker_note": "Show a practical acquisition channel."},
                {"title": "Risks", "bullets": final.get("top_concerns", ["Competition", "Trust", "Operations"])[:4], "speaker_note": "Be honest, then explain mitigation."},
                {"title": "Next Steps", "bullets": final.get("recommendations", ["Pilot", "Measure", "Iterate"])[:4], "speaker_note": "Close with a concrete plan."},
            ],
        }
