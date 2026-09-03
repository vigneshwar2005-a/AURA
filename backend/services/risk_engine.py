def risk_score(risk: str) -> int:
    """
    Convert a risk level into a numeric score.
    """

    values = {
        "LOW": 25,
        "MEDIUM": 60,
        "HIGH": 90
    }

    return values.get(str(risk).upper(), 0)


def normalize_risks(risks: list[str]) -> list[str]:
    """
    Normalize and clean risk values.
    """

    return [
        str(risk).upper().strip()
        for risk in risks
        if risk
    ]


def calculate_risk(risks: list[str]) -> dict:
    """
    AURA Unified Risk Engine.

    Combines risks from multiple agents and produces
    one overall AURA risk decision.
    """

    normalized = normalize_risks(risks)

    if not normalized:
        level = "LOW"
    elif "HIGH" in normalized:
        level = "HIGH"
    elif "MEDIUM" in normalized:
        level = "MEDIUM"
    else:
        level = "LOW"

    score = risk_score(level)

    recommendations = {
        "HIGH": "Immediate action recommended.",
        "MEDIUM": "Review and resolve the outstanding items soon.",
        "LOW": "No immediate action required."
    }

    decision_map = {
        "HIGH": "BLOCK_PAYMENT",
        "MEDIUM": "REVIEW_REQUIRED",
        "LOW": "PAYMENT_READY"
    }

    return {
        "risk_level": level,
        "risk_score": score,
        "risk_count": len(normalized),
        "risk_sources": normalized,
        "decision": decision_map[level],
        "recommendation": recommendations[level]
    }


def get_risk_summary(risk: str) -> dict:
    """
    Return a structured explanation for a single risk level.
    """

    normalized = str(risk).upper().strip()

    summaries = {
        "LOW": {
            "score": 25,
            "severity": "LOW",
            "action": "Proceed normally.",
            "description": "No significant risk detected."
        },
        "MEDIUM": {
            "score": 60,
            "severity": "MEDIUM",
            "action": "Human review recommended.",
            "description": "Some outstanding issues require review."
        },
        "HIGH": {
            "score": 90,
            "severity": "HIGH",
            "action": "Payment should be blocked.",
            "description": "A significant compliance or payment risk was detected."
        }
    }

    return summaries.get(
        normalized,
        {
            "score": 0,
            "severity": "UNKNOWN",
            "action": "Manual review required.",
            "description": "Unknown risk level."
        }
    )