from orchestrator import StartupValidationOrchestrator


def test_conflict_detection_flags_high_market_low_viability():
    orchestrator = StartupValidationOrchestrator()
    reports = {
        "market_research": {"market_analysis": "Large and rapidly growing market", "key_trends": ["strong demand"]},
        "risk_swot": {"risk_level": "Medium"},
        "viability_scorer": {"viability_score": 4.8, "competition_score": 6.5},
    }
    conflicts = orchestrator.detect_conflicts(reports)
    assert conflicts

