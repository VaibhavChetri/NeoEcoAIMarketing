"""
Neo Eco Cleaning — Sales Pipeline Manager
============================================
Deal stages, pipeline analytics, revenue forecasting, and deal aging alerts.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PIPELINE_FILE = DATA_DIR / "pipeline.json"


DEAL_STAGES = {
    "new": {"order": 0, "label": "New Lead", "color": "#6366f1"},
    "contacted": {"order": 1, "label": "Contacted", "color": "#8b5cf6"},
    "replied": {"order": 2, "label": "Replied", "color": "#3b82f6"},
    "meeting_booked": {"order": 3, "label": "Meeting Booked", "color": "#06b6d4"},
    "negotiation": {"order": 4, "label": "Negotiation", "color": "#f59e0b"},
    "won": {"order": 5, "label": "Won ✅", "color": "#10b981"},
    "lost": {"order": 6, "label": "Lost ❌", "color": "#ef4444"},
}


def _load_pipeline() -> List[Dict]:
    if PIPELINE_FILE.exists():
        with open(PIPELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_pipeline(pipeline: List[Dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(pipeline, f, indent=2, default=str)


def create_deal(
    lead_id: str,
    company_name: str,
    contact_name: str = "",
    estimated_value: float = 0,
    estimated_units: int = 0,
    product_category: str = "",
    notes: str = "",
) -> Dict:
    """Create a new deal in the pipeline."""
    pipeline = _load_pipeline()

    deal = {
        "id": f"deal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{lead_id[:4]}",
        "lead_id": lead_id,
        "company_name": company_name,
        "contact_name": contact_name,
        "stage": "new",
        "estimated_value": estimated_value,
        "estimated_units": estimated_units,
        "product_category": product_category,
        "probability": 10,
        "notes": [{"text": notes, "timestamp": datetime.now().isoformat()}] if notes else [],
        "activities": [{"action": "Deal created", "timestamp": datetime.now().isoformat()}],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_activity_at": datetime.now().isoformat(),
        "expected_close_date": (datetime.now() + timedelta(days=90)).isoformat(),
    }

    pipeline.append(deal)
    _save_pipeline(pipeline)
    return deal


def update_deal_stage(deal_id: str, new_stage: str, note: str = "") -> bool:
    """Move a deal to a new stage."""
    if new_stage not in DEAL_STAGES:
        return False

    pipeline = _load_pipeline()
    probability_map = {
        "new": 10, "contacted": 15, "replied": 30,
        "meeting_booked": 50, "negotiation": 70, "won": 100, "lost": 0,
    }

    for deal in pipeline:
        if deal["id"] == deal_id:
            old_stage = deal["stage"]
            deal["stage"] = new_stage
            deal["probability"] = probability_map.get(new_stage, 10)
            deal["updated_at"] = datetime.now().isoformat()
            deal["last_activity_at"] = datetime.now().isoformat()

            deal["activities"].append({
                "action": f"Stage changed: {old_stage} → {new_stage}",
                "timestamp": datetime.now().isoformat(),
            })

            if note:
                deal["notes"].append({"text": note, "timestamp": datetime.now().isoformat()})

            _save_pipeline(pipeline)
            return True
    return False


def get_deal(deal_id: str) -> Optional[Dict]:
    for deal in _load_pipeline():
        if deal["id"] == deal_id:
            return deal
    return None


def get_all_deals() -> List[Dict]:
    return _load_pipeline()


def get_deals_by_stage(stage: str) -> List[Dict]:
    return [d for d in _load_pipeline() if d["stage"] == stage]


def get_pipeline_view() -> Dict:
    """Get a Kanban-style pipeline view."""
    pipeline = _load_pipeline()
    view = {}

    for stage_key, stage_info in DEAL_STAGES.items():
        stage_deals = [d for d in pipeline if d["stage"] == stage_key]
        view[stage_key] = {
            "label": stage_info["label"],
            "color": stage_info["color"],
            "count": len(stage_deals),
            "total_value": sum(d.get("estimated_value", 0) for d in stage_deals),
            "deals": stage_deals,
        }

    return view


def get_pipeline_analytics() -> Dict:
    """Get comprehensive pipeline analytics."""
    pipeline = _load_pipeline()
    if not pipeline:
        return {"message": "No deals in pipeline"}

    total_deals = len(pipeline)
    active_deals = [d for d in pipeline if d["stage"] not in ("won", "lost")]
    won_deals = [d for d in pipeline if d["stage"] == "won"]
    lost_deals = [d for d in pipeline if d["stage"] == "lost"]

    total_pipeline_value = sum(d.get("estimated_value", 0) for d in active_deals)
    weighted_pipeline = sum(
        d.get("estimated_value", 0) * d.get("probability", 0) / 100
        for d in active_deals
    )

    stages_count = {}
    for d in pipeline:
        stages_count[d["stage"]] = stages_count.get(d["stage"], 0) + 1

    stale_deals = []
    for d in active_deals:
        last_activity = datetime.fromisoformat(d.get("last_activity_at", d["created_at"]))
        days_since = (datetime.now() - last_activity).days
        if days_since > 14:
            stale_deals.append({
                "deal_id": d["id"],
                "company": d["company_name"],
                "stage": d["stage"],
                "days_inactive": days_since,
                "value": d.get("estimated_value", 0),
            })

    closed_deals = len(won_deals) + len(lost_deals)
    win_rate = (len(won_deals) / closed_deals * 100) if closed_deals > 0 else 0

    return {
        "total_deals": total_deals,
        "active_deals": len(active_deals),
        "won_deals": len(won_deals),
        "lost_deals": len(lost_deals),
        "win_rate": f"{win_rate:.1f}%",
        "total_pipeline_value": total_pipeline_value,
        "weighted_pipeline_value": round(weighted_pipeline, 2),
        "won_revenue": sum(d.get("estimated_value", 0) for d in won_deals),
        "by_stage": stages_count,
        "stale_deals": sorted(stale_deals, key=lambda x: -x["days_inactive"]),
        "average_deal_value": round(
            sum(d.get("estimated_value", 0) for d in pipeline) / max(total_deals, 1), 2
        ),
    }


def get_revenue_forecast(months: int = 3) -> Dict:
    """Forecast revenue based on pipeline probability."""
    pipeline = _load_pipeline()
    active_deals = [d for d in pipeline if d["stage"] not in ("won", "lost")]

    forecast = {
        "period": f"Next {months} months",
        "optimistic": sum(d.get("estimated_value", 0) for d in active_deals),
        "weighted": sum(
            d.get("estimated_value", 0) * d.get("probability", 0) / 100
            for d in active_deals
        ),
        "conservative": sum(
            d.get("estimated_value", 0) * d.get("probability", 0) / 100
            for d in active_deals
            if d.get("probability", 0) >= 50
        ),
        "deals_by_probability": {
            "high (70%+)": [d for d in active_deals if d.get("probability", 0) >= 70],
            "medium (30-69%)": [d for d in active_deals if 30 <= d.get("probability", 0) < 70],
            "low (<30%)": [d for d in active_deals if d.get("probability", 0) < 30],
        },
    }

    return forecast
