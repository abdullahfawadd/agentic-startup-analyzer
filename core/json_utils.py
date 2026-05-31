from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(raw: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract a JSON object from model text that may contain markdown or prose."""
    fallback = fallback or {}
    if not raw:
        return fallback

    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return fallback


def ensure_list(value: Any, default: list[Any] | None = None) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return default or []
    return [value]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))

