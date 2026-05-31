from __future__ import annotations

from typing import Any

from groq import Groq

from core.config import Settings
from core.json_utils import extract_json_object


class LLMUnavailable(RuntimeError):
    """Raised when an LLM-backed step cannot run and no fallback should be used."""


class GroqLLM:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Groq | None = None
        if settings.groq_api_key:
            self._client = Groq(api_key=settings.groq_api_key, timeout=settings.api_timeout_seconds)

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete_text(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> str:
        if not self._client:
            raise LLMUnavailable("Groq API key is not configured.")
        response = self._client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        fallback: dict[str, Any],
        temperature: float = 0.15,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        raw = self.complete_text(system, user, temperature=temperature, max_tokens=max_tokens)
        return extract_json_object(raw, fallback=fallback)

