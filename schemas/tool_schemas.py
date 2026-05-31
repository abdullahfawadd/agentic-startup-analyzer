BUSINESS_TOOL_SCHEMAS = [
    {
        "name": "estimate_market_potential",
        "description": "Estimate market attractiveness, TAM, and growth rate for an industry and geography.",
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string"},
                "geography": {"type": "string"},
                "target_segment": {"type": "string"},
            },
            "required": ["industry", "geography", "target_segment"],
        },
    },
    {
        "name": "check_competition_level",
        "description": "Estimate competition density and differentiation strength for the startup domain.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "unique_value_prop": {"type": "string"},
            },
            "required": ["domain", "unique_value_prop"],
        },
    },
    {
        "name": "calculate_viability_score",
        "description": "Calculate an overall viability score using market, competition, team, and timeline inputs.",
        "parameters": {
            "type": "object",
            "properties": {
                "market_score": {"type": "number"},
                "competition_score": {"type": "number"},
                "team_size": {"type": "integer"},
                "timeline_months": {"type": "integer"},
            },
            "required": ["market_score", "competition_score", "team_size", "timeline_months"],
        },
    },
]

