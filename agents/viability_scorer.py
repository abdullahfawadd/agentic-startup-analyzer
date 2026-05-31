from __future__ import annotations

from typing import Any, Callable

from core.json_utils import ensure_list
from core.llm import GroqLLM
from schemas.tool_schemas import BUSINESS_TOOL_SCHEMAS
from tools.business_tools import (
    calculate_viability_score,
    check_competition_level,
    estimate_market_potential,
)


class ViabilityScorerAgent:
    def __init__(self, llm: GroqLLM):
        self.llm = llm
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {
            "estimate_market_potential": estimate_market_potential,
            "check_competition_level": check_competition_level,
            "calculate_viability_score": calculate_viability_score,
        }

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        plan = self._tool_plan(payload)
        tools_called: list[dict[str, Any]] = []
        context: dict[str, Any] = {}

        for step in plan:
            tool_name = step["tool_name"]
            args = self._resolve_args(tool_name, step.get("arguments", {}), payload, context)
            result = self.tools[tool_name](**args)
            tools_called.append({"tool_name": tool_name, "arguments": args, "result": result})
            context[tool_name] = result

        market = context["estimate_market_potential"]
        competition = context["check_competition_level"]
        viability = context["calculate_viability_score"]
        return {
            "status": "complete" if self.llm.available else "degraded",
            "executive_summary": f"{viability['verdict']} with a {viability['viability_score']}/10 score and {viability['revenue_potential']} revenue potential.",
            "viability_score": viability["viability_score"],
            "market_score": market["market_score"],
            "competition_score": competition["competition_score"],
            "revenue_potential": viability["revenue_potential"],
            "go_to_market_readiness": viability["go_to_market_readiness"],
            "verdict": viability["verdict"],
            "tools_called": tools_called,
            "turn_count": len(tools_called),
        }

    def _tool_plan(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        fallback = self._default_plan(payload)
        if not self.llm.available:
            return fallback

        system = (
            "You are a Tool Use agent. Choose only from the provided tools and return strict JSON. "
            "The correct plan should estimate market potential, check competition, then calculate viability."
        )
        user = f"""
Startup payload:
{payload}

Available tools:
{BUSINESS_TOOL_SCHEMAS}

Return JSON:
{{"tool_calls": [{{"tool_name": "...", "arguments": {{}}}}]}}
"""
        response = self.llm.complete_json(system, user, fallback={"tool_calls": fallback}, max_tokens=900)
        calls = ensure_list(response.get("tool_calls"), fallback)
        allowed = []
        for call in calls:
            if isinstance(call, dict) and call.get("tool_name") in self.tools:
                allowed.append(call)
        names = [call["tool_name"] for call in allowed]
        if names != ["estimate_market_potential", "check_competition_level", "calculate_viability_score"]:
            return fallback
        return allowed

    def _default_plan(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "tool_name": "estimate_market_potential",
                "arguments": {
                    "industry": payload["industry"],
                    "geography": payload["geography"],
                    "target_segment": payload["target_market"],
                },
            },
            {
                "tool_name": "check_competition_level",
                "arguments": {
                    "domain": payload["industry"],
                    "unique_value_prop": payload.get("unique_value_prop") or payload["idea_description"],
                },
            },
            {
                "tool_name": "calculate_viability_score",
                "arguments": {
                    "market_score": "$estimate_market_potential.market_score",
                    "competition_score": "$check_competition_level.competition_score",
                    "team_size": payload["team_size"],
                    "timeline_months": payload["timeline_months"],
                },
            },
        ]

    def _resolve_args(
        self,
        tool_name: str,
        args: dict[str, Any],
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_name == "estimate_market_potential":
            return {
                "industry": str(args.get("industry") or payload["industry"]),
                "geography": str(args.get("geography") or payload["geography"]),
                "target_segment": str(args.get("target_segment") or payload["target_market"]),
            }
        if tool_name == "check_competition_level":
            return {
                "domain": str(args.get("domain") or payload["industry"]),
                "unique_value_prop": str(args.get("unique_value_prop") or payload.get("unique_value_prop") or payload["idea_description"]),
            }
        return {
            "market_score": float(context["estimate_market_potential"]["market_score"]),
            "competition_score": float(context["check_competition_level"]["competition_score"]),
            "team_size": int(payload["team_size"]),
            "timeline_months": int(payload["timeline_months"]),
        }

