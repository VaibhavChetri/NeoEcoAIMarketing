"""
Neo Eco Cleaning — Lead Scorer
================================
Score leads based on ICP match: company type, location, industry, engagement.
"""

import yaml
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "neo_eco_config.yaml"


def _load_config() -> Dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_lead(lead: Dict) -> Dict:
    """
    Score a lead 0-100 based on ICP match.
    Returns detailed scoring breakdown.
    """
    config = _load_config()
    icp = config.get("ideal_customer_profile", {})
    weights = icp.get("scoring_weights", {
        "company_size": 0.15,
        "industry_match": 0.30,
        "location_match": 0.25,
        "engagement": 0.30,
    })

    scores = {}

    # --- Company Size Score ---
    try:
        employees = int(str(lead.get("employees", "0")).replace(",", ""))
    except (ValueError, TypeError):
        employees = 0

    min_emp = icp.get("company_size", {}).get("min_employees", 1)
    max_emp = icp.get("company_size", {}).get("max_employees", 500)

    if min_emp <= employees <= max_emp:
        mid = (min_emp + max_emp) / 2
        distance = abs(employees - mid) / mid
        scores["company_size"] = max(100 - int(distance * 50), 60)
    elif employees > 0:
        scores["company_size"] = 30
    else:
        scores["company_size"] = 10

    # --- Industry Match Score ---
    lead_industry = lead.get("industry", "").lower()
    target_types = [t.lower() for t in icp.get("company_types", [])]

    industry_keywords = [
        "property management", "block management", "building management",
        "estate agent", "letting agent", "facilities management",
        "real estate", "housing association", "property", "building",
        "estate", "residential", "commercial property",
    ]

    if any(t in lead_industry for t in target_types):
        scores["industry_match"] = 100
    elif any(k in lead_industry for k in industry_keywords):
        scores["industry_match"] = 75
    elif lead_industry:
        scores["industry_match"] = 20
    else:
        scores["industry_match"] = 10

    # --- Location Match Score ---
    lead_country = lead.get("country", "").lower()
    target_locations = [loc.lower() for loc in icp.get("locations", [])]

    if any(loc in lead_country for loc in target_locations):
        # Priority boroughs get highest scores
        priority = ["barnet", "enfield", "camden", "islington", "haringey", "north london"]
        if any(p in lead_country for p in priority):
            scores["location_match"] = 100
        else:
            scores["location_match"] = 85
    elif "london" in lead_country:
        scores["location_match"] = 70
    elif lead_country:
        scores["location_match"] = 20
    else:
        scores["location_match"] = 10

    # --- Engagement Score ---
    engagement = 0

    contacts = lead.get("contacts", [])
    if any(c.get("email") for c in contacts):
        engagement += 30
    if any(c.get("name") for c in contacts):
        engagement += 10

    if lead.get("company_phone"):
        engagement += 10
    if lead.get("company_linkedin"):
        engagement += 10
    if lead.get("website"):
        engagement += 10
    if lead.get("about"):
        engagement += 10

    stage = lead.get("stage", "new")
    stage_boost = {
        "new": 0, "contacted": 10, "replied": 30,
        "meeting_booked": 40, "negotiation": 50,
    }
    engagement += stage_boost.get(stage, 0)

    if lead.get("campaigns"):
        engagement += 10

    scores["engagement"] = min(engagement, 100)

    # --- Calculate Overall Score ---
    overall = sum(scores[k] * weights.get(k, 0.25) for k in scores)
    scores["overall"] = round(overall, 1)

    # --- Grade ---
    if overall >= 80:
        scores["grade"] = "A"
        scores["recommendation"] = "High priority — reach out immediately"
    elif overall >= 60:
        scores["grade"] = "B"
        scores["recommendation"] = "Good fit — include in next campaign"
    elif overall >= 40:
        scores["grade"] = "C"
        scores["recommendation"] = "Moderate fit — research further before outreach"
    else:
        scores["grade"] = "D"
        scores["recommendation"] = "Low fit — deprioritize or remove"

    # --- Reason Synthesis ---
    reasons = []
    if scores.get("location_match", 0) == 100:
        reasons.append(f"Priority North London area ({lead_country.title()}).")
    elif scores.get("location_match", 0) >= 85:
        reasons.append(f"Good London location ({lead_country.title()}).")

    if scores.get("industry_match", 0) == 100:
        reasons.append("Exact industry match (property/building management).")
    elif scores.get("industry_match", 0) >= 75:
        reasons.append("Relevant industry alignment.")

    if scores.get("company_size", 0) >= 60:
        reasons.append("Suitable company size.")

    if scores.get("engagement", 0) >= 40:
        reasons.append("High engagement.")
    elif scores.get("engagement", 0) >= 20:
        reasons.append("Direct contact data available.")

    if not reasons:
        reasons.append("Does not strongly align with targets.")

    scores["reason"] = " ".join(reasons)

    return scores


def score_all_leads(leads: List[Dict]) -> List[Dict]:
    """Score all leads and return sorted by score (highest first)."""
    scored = []
    for lead in leads:
        lead_score = score_lead(lead)
        scored.append({
            "lead_id": lead.get("id", ""),
            "company_name": lead.get("company_name", ""),
            "country": lead.get("country", ""),
            "industry": lead.get("industry", ""),
            "stage": lead.get("stage", "new"),
            **lead_score,
        })

    return sorted(scored, key=lambda x: -x["overall"])


def get_score_distribution(leads: List[Dict]) -> Dict:
    """Get distribution of lead scores."""
    scored = score_all_leads(leads)

    distribution = {"A": [], "B": [], "C": [], "D": []}
    for s in scored:
        distribution[s["grade"]].append(s["company_name"])

    return {
        "total_scored": len(scored),
        "grade_counts": {g: len(leads) for g, leads in distribution.items()},
        "grade_details": distribution,
        "average_score": round(
            sum(s["overall"] for s in scored) / max(len(scored), 1), 1
        ),
        "top_10": scored[:10],
    }
