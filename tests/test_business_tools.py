from tools.business_tools import (
    calculate_viability_score,
    check_competition_level,
    estimate_market_potential,
)


def test_market_potential_for_pakistan_ecommerce_is_strong():
    result = estimate_market_potential("e-commerce", "Pakistan", "families and small retailers")
    assert result["market_score"] >= 8
    assert "tam" in result


def test_group_buying_improves_differentiation():
    result = check_competition_level("e-commerce", "AI group buying and bulk purchasing")
    assert result["competition_score"] >= 6
    assert result["density"] in {"Medium", "High"}


def test_viability_score_is_bounded():
    result = calculate_viability_score(8, 6, team_size=3, timeline_months=8)
    assert 1 <= result["viability_score"] <= 10
    assert result["verdict"] in {"HIGHLY VIABLE", "VIABLE WITH CAUTION", "NEEDS VALIDATION", "HIGH RISK"}

