from __future__ import annotations

from typing import Any

from core.config import Settings
from core.json_utils import ensure_list
from core.llm import GroqLLM
from tools.search_tools import SearchTools


class MarketResearchAgent:
    def __init__(self, settings: Settings, llm: GroqLLM):
        self.settings = settings
        self.llm = llm
        self.search = SearchTools(settings)

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        startup = payload["startup_name"]
        industry = payload["industry"]
        geography = payload["geography"]
        target = payload["target_market"]
        idea = payload["idea_description"]

        query_plan = [
            (
                "I need current market sizing and growth signals before judging the opportunity.",
                f"{industry} market size {geography} 2025 growth startup opportunity",
            ),
            (
                "I need to identify direct and adjacent competitors in the target geography.",
                f"{startup} competitors {industry} {geography} startups marketplace",
            ),
            (
                "I need recent customer behavior and trend signals for this target market.",
                f"{target} pain points {industry} {geography} digital commerce trends",
            ),
        ]

        trace: list[str] = []
        observations: list[dict[str, Any]] = []
        status = "complete"
        search_failures = 0

        for index, (thought, query) in enumerate(query_plan):
            trace.append(f"THOUGHT: {thought}")
            trace.append(f"ACTION: web_search({query!r})")
            try:
                result = self.search.web_search(query, max_results=3, include_images=index == 0)
                observations.append(result)
                snippet = result.get("answer") or "Returned ranked market sources and competitor references."
                trace.append(f"OBSERVATION: {snippet[:360]}")
            except Exception as exc:
                search_failures += 1
                status = "degraded"
                fallback = {
                    "query": query,
                    "answer": f"Search unavailable, using model and heuristic market reasoning. Reason: {type(exc).__name__}.",
                    "results": [],
                }
                observations.append(fallback)
                trace.append("OBSERVATION: Live search unavailable; continuing with fallback market assumptions.")

        wiki_summary: dict[str, str] = {"topic": industry, "summary": "", "url": ""}
        try:
            wiki_summary = self.search.get_wikipedia_summary(industry)
            if wiki_summary.get("summary"):
                trace.append(f"ACTION: get_wikipedia_summary({industry!r})")
                trace.append(f"OBSERVATION: {wiki_summary['summary'][:300]}")
        except Exception:
            if search_failures == len(query_plan):
                status = "degraded"
            elif status == "complete":
                status = "complete_with_notes"

        fallback = self._fallback_report(payload, trace, status)
        if not self.llm.available:
            return fallback

        system = (
            "You are a senior startup market research analyst. Return strict JSON only. "
            "Be specific, cite useful signals from observations, and avoid invented source URLs."
        )
        llm_observations = [
            {key: value for key, value in observation.items() if key != "images"}
            for observation in observations
        ]
        user = f"""
Startup: {startup}
Idea: {idea}
Industry: {industry}
Target market: {target}
Geography: {geography}

ReAct observations:
{llm_observations}

Wikipedia context:
{wiki_summary}

Return JSON with these keys:
market_analysis, estimated_market_size, top_competitors, key_trends,
customer_pain_points, executive_summary.
"""
        report = self.llm.complete_json(system, user, fallback=fallback, max_tokens=900)
        report["top_competitors"] = ensure_list(report.get("top_competitors"), fallback["top_competitors"])[:5]
        report["key_trends"] = ensure_list(report.get("key_trends"), fallback["key_trends"])[:5]
        report["customer_pain_points"] = ensure_list(
            report.get("customer_pain_points"),
            fallback["customer_pain_points"],
        )[:5]
        report["react_turns"] = len(query_plan)
        report["reasoning_trace"] = trace + ["FINAL ANSWER: Market report synthesized from ReAct observations."]
        report["status"] = status
        report["sources"] = self._sources_from_observations(observations, wiki_summary)
        report["media"] = self._media_from_observations(observations)
        return report

    def _fallback_report(self, payload: dict[str, Any], trace: list[str], status: str) -> dict[str, Any]:
        geography = payload["geography"]
        industry = payload["industry"]
        target = payload["target_market"]
        return {
            "status": status,
            "executive_summary": f"{payload['startup_name']} targets a meaningful {industry} opportunity in {geography}, but the go-to-market must prove repeat purchase behavior quickly.",
            "market_analysis": f"The idea sits in a fragmented {industry} market where digital adoption, convenience, and price sensitivity create room for a focused entrant. In {geography}, the strongest wedge is likely a narrow launch segment within {target} rather than a broad all-customer rollout.",
            "estimated_market_size": "$500M-$2B addressable segment",
            "top_competitors": ["Local marketplaces", "Grocery delivery apps", "Traditional retailers", "Social commerce sellers"],
            "key_trends": ["AI-assisted commerce", "Price-sensitive buying", "Community-led purchasing", "Mobile-first discovery"],
            "customer_pain_points": ["High prices", "Trust gaps", "Inconsistent delivery", "Limited transparent comparisons"],
            "react_turns": 3,
            "reasoning_trace": trace + ["FINAL ANSWER: Fallback report generated because live research was unavailable."],
            "sources": [],
            "media": [],
        }

    def _sources_from_observations(self, observations: list[dict[str, Any]], wiki: dict[str, str]) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        for observation in observations:
            for result in observation.get("results", []):
                if result.get("url"):
                    sources.append({"title": result.get("title", "Source"), "url": result["url"]})
        if wiki.get("url"):
            sources.append({"title": f"Wikipedia: {wiki.get('topic', 'Industry')}", "url": wiki["url"]})
        return sources[:8]

    def _media_from_observations(self, observations: list[dict[str, Any]]) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        seen: set[str] = set()
        for observation in observations:
            for image_url in observation.get("images", []):
                if image_url in seen:
                    continue
                seen.add(image_url)
                images.append({"title": "Market visual evidence", "url": image_url})
        return images[:6]
