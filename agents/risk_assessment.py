from __future__ import annotations

from typing import Any

from core.json_utils import ensure_list
from core.llm import GroqLLM


class RiskAssessmentAgent:
    def __init__(self, llm: GroqLLM):
        self.llm = llm

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        fallback = self._fallback_swot(payload, critiques=["SWOT APPROVED"], rounds=1, approved=True, status="degraded")
        if not self.llm.available:
            return fallback

        current = self._generate(payload)
        critiques: list[str] = []
        approved = False

        for round_index in range(1, 4):
            critique = self._critique(payload, current)
            critiques.append(critique)
            if critique.strip() == "SWOT APPROVED":
                approved = True
                break
            current = self._revise(payload, current, critique, round_index + 1)

        normalized = self._normalize(current, fallback)
        normalized["reflection_rounds"] = len(critiques)
        normalized["approved"] = approved
        normalized["critiques"] = critiques
        normalized["status"] = "complete" if approved else "complete_with_notes"
        normalized["executive_summary"] = self._summary(normalized)
        return normalized

    def _generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        system = "You are a blunt startup risk analyst. Return strict JSON only."
        user = f"""
Create a specific SWOT and risk assessment for:
{payload}

Return JSON:
{{
  "swot": {{"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}},
  "risk_level": "Low|Medium|High",
  "key_risks": []
}}
"""
        return self.llm.complete_json(system, user, fallback=self._fallback_swot(payload, [], 1, False, "degraded"))

    def _critique(self, payload: dict[str, Any], swot: dict[str, Any]) -> str:
        system = (
            "You are a critic for a Reflection-pattern agent. Check Specificity, Honesty, Evidence, "
            "Realism, and Balance. If there are no issues, output exactly SWOT APPROVED."
        )
        user = f"Startup context:\n{payload}\n\nSWOT draft:\n{swot}\n\nReturn critique text only."
        return self.llm.complete_text(system, user, temperature=0.1, max_tokens=500).strip()

    def _revise(self, payload: dict[str, Any], swot: dict[str, Any], critique: str, round_number: int) -> dict[str, Any]:
        system = "You revise SWOT analyses based on critic feedback. Return strict JSON only."
        user = f"""
Startup context:
{payload}

Current SWOT:
{swot}

Critique to address:
{critique}

Revision round: {round_number}
Return the same JSON shape with sharper, more specific content.
"""
        return self.llm.complete_json(system, user, fallback=swot)

    def _normalize(self, data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        swot = data.get("swot") if isinstance(data.get("swot"), dict) else fallback["swot"]
        return {
            "swot": {
                "strengths": ensure_list(swot.get("strengths"), fallback["swot"]["strengths"])[:5],
                "weaknesses": ensure_list(swot.get("weaknesses"), fallback["swot"]["weaknesses"])[:5],
                "opportunities": ensure_list(swot.get("opportunities"), fallback["swot"]["opportunities"])[:5],
                "threats": ensure_list(swot.get("threats"), fallback["swot"]["threats"])[:5],
            },
            "risk_level": data.get("risk_level") or fallback["risk_level"],
            "key_risks": ensure_list(data.get("key_risks"), fallback["key_risks"])[:5],
        }

    def _fallback_swot(
        self,
        payload: dict[str, Any],
        critiques: list[str],
        rounds: int,
        approved: bool,
        status: str,
    ) -> dict[str, Any]:
        startup = payload["startup_name"]
        industry = payload["industry"]
        return {
            "status": status,
            "executive_summary": f"{startup} has a credible wedge, but execution risk depends on customer acquisition cost, trust, and operational focus.",
            "swot": {
                "strengths": [
                    f"Clear problem framing in {industry}",
                    "Can start with a narrow launch segment before scaling",
                    "AI-assisted analysis can improve targeting and recommendations",
                ],
                "weaknesses": [
                    "Marketplace trust and liquidity are difficult to build early",
                    "Operational complexity may rise faster than the product team expects",
                    "Value proposition must be sharper than convenience alone",
                ],
                "opportunities": [
                    "Price-sensitive customers may respond strongly to measurable savings",
                    "Partnerships with local suppliers can create defensible supply",
                    "Data from early cohorts can improve personalization and retention",
                ],
                "threats": [
                    "Incumbent marketplaces can copy visible features",
                    "Customer acquisition costs may outpace order margins",
                    "Supplier reliability issues can damage trust quickly",
                ],
            },
            "risk_level": "Medium",
            "key_risks": ["Liquidity risk", "Customer acquisition cost", "Operational reliability", "Competitive response"],
            "reflection_rounds": rounds,
            "approved": approved,
            "critiques": critiques,
        }

    def _summary(self, report: dict[str, Any]) -> str:
        return f"Risk level is {report['risk_level']}; the biggest issues are {', '.join(report['key_risks'][:2])}."

