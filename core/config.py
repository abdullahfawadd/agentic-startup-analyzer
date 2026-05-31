from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Startup Idea Validator"
    app_env: str = os.getenv("APP_ENV", "development")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    api_timeout_seconds: int = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
    allow_demo_fallback: bool = _as_bool(os.getenv("ALLOW_DEMO_FALLBACK"), True)

    @property
    def groq_ready(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def tavily_ready(self) -> bool:
        return bool(self.tavily_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

