from __future__ import annotations

from typing import Any

import requests
from tavily import TavilyClient

from core.config import Settings


class SearchTools:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._tavily = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None

    def web_search(self, query: str, *, max_results: int = 4) -> dict[str, Any]:
        if not self._tavily:
            raise RuntimeError("Tavily API key is not configured.")
        response = self._tavily.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )
        return {
            "query": query,
            "answer": response.get("answer") or "",
            "results": [
                {
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:700],
                    "score": item.get("score"),
                }
                for item in response.get("results", [])
            ],
        }

    def get_wikipedia_summary(self, topic: str) -> dict[str, str]:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic)}"
        response = requests.get(url, timeout=self.settings.api_timeout_seconds)
        if response.status_code == 404:
            return {"topic": topic, "summary": "", "url": ""}
        response.raise_for_status()
        payload = response.json()
        return {
            "topic": topic,
            "summary": payload.get("extract", "")[:900],
            "url": payload.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
