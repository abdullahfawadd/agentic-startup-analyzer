from __future__ import annotations

from core.json_utils import clamp


MARKET_DATA = {
    ("e-commerce", "pakistan"): {"market_score": 8.2, "tam": "$7.7B", "growth_rate": "18-24%", "maturity": "rapidly growing"},
    ("commerce", "pakistan"): {"market_score": 8.0, "tam": "$7.7B", "growth_rate": "18-24%", "maturity": "rapidly growing"},
    ("fintech", "pakistan"): {"market_score": 8.4, "tam": "$4.0B", "growth_rate": "20-28%", "maturity": "high growth"},
    ("healthtech", "pakistan"): {"market_score": 7.4, "tam": "$1.5B", "growth_rate": "14-20%", "maturity": "emerging"},
    ("edtech", "pakistan"): {"market_score": 7.1, "tam": "$1.2B", "growth_rate": "12-18%", "maturity": "competitive"},
    ("saas", "global"): {"market_score": 8.0, "tam": "$250B+", "growth_rate": "13-18%", "maturity": "mature but expanding"},
    ("ai", "global"): {"market_score": 8.8, "tam": "$300B+", "growth_rate": "25-35%", "maturity": "hyper growth"},
}


def _norm(value: str) -> str:
    return value.strip().lower()


def _industry_bucket(industry: str) -> str:
    value = _norm(industry)
    if any(token in value for token in ["commerce", "retail", "grocery", "marketplace"]):
        return "e-commerce"
    if "fin" in value or "payment" in value:
        return "fintech"
    if "health" in value or "medical" in value:
        return "healthtech"
    if "education" in value or "edtech" in value:
        return "edtech"
    if "ai" in value or "genai" in value:
        return "ai"
    if "saas" in value or "software" in value:
        return "saas"
    return value or "general"


def estimate_market_potential(industry: str, geography: str, target_segment: str) -> dict:
    bucket = _industry_bucket(industry)
    geo = _norm(geography)
    data = MARKET_DATA.get((bucket, geo)) or MARKET_DATA.get((bucket, "global"))
    if not data:
        base = 6.6
        if geo in {"pakistan", "india", "uae", "saudi arabia"}:
            base += 0.4
        if any(token in _norm(target_segment) for token in ["sme", "students", "families", "b2b", "retailers"]):
            base += 0.3
        data = {"market_score": base, "tam": "$500M-$2B", "growth_rate": "10-16%", "maturity": "fragmented"}
    return {
        "market_score": round(clamp(float(data["market_score"]), 1, 10), 1),
        "tam": data["tam"],
        "growth_rate": data["growth_rate"],
        "maturity": data["maturity"],
        "rationale": f"{industry} in {geography} shows {data['maturity']} demand for {target_segment}.",
    }


def check_competition_level(domain: str, unique_value_prop: str) -> dict:
    combined = f"{domain} {unique_value_prop}".lower()
    density = "Medium"
    known_players = 5
    differentiation_score = 6.2

    if any(token in combined for token in ["grocery", "e-commerce", "marketplace", "delivery"]):
        density = "High"
        known_players = 9
        differentiation_score = 5.8
    if any(token in combined for token in ["bulk", "group buying", "pooling", "community"]):
        density = "Medium"
        known_players = max(known_players - 2, 3)
        differentiation_score += 1.1
    if any(token in combined for token in ["ai", "agent", "personalized", "predictive"]):
        differentiation_score += 0.7
    if any(token in combined for token in ["regulated", "banking", "insurance"]):
        density = "High"
        known_players += 3
        differentiation_score -= 0.5

    differentiation_score = round(clamp(differentiation_score, 1, 10), 1)
    return {
        "density": density,
        "known_players": known_players,
        "differentiation_score": differentiation_score,
        "competition_score": differentiation_score,
        "rationale": "Differentiation improves when the concept has a clear wedge beyond a standard marketplace.",
    }


def calculate_viability_score(
    market_score: float,
    competition_score: float,
    team_size: int,
    timeline_months: int,
) -> dict:
    team_score = clamp(4.5 + min(team_size, 8) * 0.55, 1, 10)
    timeline_score = 8.0 if 4 <= timeline_months <= 12 else 6.3 if timeline_months <= 18 else 5.2
    execution_score = (team_score * 0.6) + (timeline_score * 0.4)
    viability_score = (market_score * 0.45) + (competition_score * 0.30) + (execution_score * 0.25)
    viability_score = round(clamp(viability_score, 1, 10), 1)

    if viability_score >= 8:
        verdict = "HIGHLY VIABLE"
        revenue_potential = "High"
        readiness = "Strong"
    elif viability_score >= 6.8:
        verdict = "VIABLE WITH CAUTION"
        revenue_potential = "Medium-High"
        readiness = "Promising"
    elif viability_score >= 5.5:
        verdict = "NEEDS VALIDATION"
        revenue_potential = "Medium"
        readiness = "Early"
    else:
        verdict = "HIGH RISK"
        revenue_potential = "Low-Medium"
        readiness = "Weak"

    return {
        "viability_score": viability_score,
        "execution_score": round(execution_score, 1),
        "revenue_potential": revenue_potential,
        "go_to_market_readiness": readiness,
        "verdict": verdict,
    }

