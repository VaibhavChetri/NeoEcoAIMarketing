"""
Neo Eco Cleaning — Campaign Tracker
======================================
Track campaign performance: opens, replies, bounces, conversions.
Generate performance reports and learning insights.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CAMPAIGNS_FILE = BASE_DIR / "data" / "campaigns.json"
SEND_LOG_DIR = BASE_DIR / "output" / "send_logs"


def _load_campaigns() -> List[Dict]:
    if CAMPAIGNS_FILE.exists():
        with open(CAMPAIGNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_campaigns(campaigns: List[Dict]):
    CAMPAIGNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CAMPAIGNS_FILE, "w", encoding="utf-8") as f:
        json.dump(campaigns, f, indent=2, default=str)


def create_campaign(
    name: str,
    email_type: str,
    target_countries: List[str] = None,
    target_industries: List[str] = None,
    description: str = "",
) -> Dict:
    """Create a new campaign record."""
    campaigns = _load_campaigns()

    campaign = {
        "id": f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "name": name,
        "email_type": email_type,
        "description": description,
        "target_countries": target_countries or [],
        "target_industries": target_industries or [],
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "stats": {
            "total_leads": 0,
            "emails_generated": 0,
            "emails_sent": 0,
            "emails_opened": 0,
            "replies": 0,
            "bounces": 0,
            "opt_outs": 0,
            "meetings_booked": 0,
        },
    }

    campaigns.append(campaign)
    _save_campaigns(campaigns)
    return campaign


def get_campaign(campaign_id: str) -> Optional[Dict]:
    for c in _load_campaigns():
        if c["id"] == campaign_id:
            return c
    return None


def get_all_campaigns() -> List[Dict]:
    return _load_campaigns()


def update_campaign_status(campaign_id: str, status: str) -> bool:
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            c["status"] = status
            if status == "running":
                c["started_at"] = datetime.now().isoformat()
            elif status in ("completed", "paused"):
                c["completed_at"] = datetime.now().isoformat()
            _save_campaigns(campaigns)
            return True
    return False


def update_campaign_stats(campaign_id: str, stats_update: Dict) -> bool:
    """Update campaign statistics."""
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            for key, value in stats_update.items():
                if key in c.get("stats", {}):
                    c["stats"][key] = value
            _save_campaigns(campaigns)
            return True
    return False


def record_reply(campaign_id: str, lead_id: str, reply_type: str = "positive") -> bool:
    """Record a reply to a campaign email."""
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            c["stats"]["replies"] = c["stats"].get("replies", 0) + 1
            c.setdefault("replies_log", []).append({
                "lead_id": lead_id,
                "reply_type": reply_type,
                "timestamp": datetime.now().isoformat(),
            })
            _save_campaigns(campaigns)
            return True
    return False


def record_meeting(campaign_id: str, lead_id: str) -> bool:
    """Record a meeting booked from a campaign."""
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            c["stats"]["meetings_booked"] = c["stats"].get("meetings_booked", 0) + 1
            c.setdefault("meetings_log", []).append({
                "lead_id": lead_id,
                "timestamp": datetime.now().isoformat(),
            })
            _save_campaigns(campaigns)
            return True
    return False


def get_campaign_report(campaign_id: str) -> Dict:
    """Generate a detailed campaign performance report."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        return {"error": "Campaign not found"}

    stats = campaign.get("stats", {})
    sent = max(stats.get("emails_sent", 0), 1)

    report = {
        "campaign": campaign["name"],
        "campaign_id": campaign_id,
        "status": campaign["status"],
        "email_type": campaign["email_type"],
        "created_at": campaign["created_at"],
        "stats": stats,
        "rates": {
            "open_rate": f"{(stats.get('emails_opened', 0) / sent * 100):.1f}%",
            "reply_rate": f"{(stats.get('replies', 0) / sent * 100):.1f}%",
            "bounce_rate": f"{(stats.get('bounces', 0) / sent * 100):.1f}%",
            "meeting_rate": f"{(stats.get('meetings_booked', 0) / sent * 100):.1f}%",
            "opt_out_rate": f"{(stats.get('opt_outs', 0) / sent * 100):.1f}%",
        },
        "benchmarks": {
            "open_rate": "40-55% (B2B services average)",
            "reply_rate": "5-12% (B2B services average)",
            "meeting_rate": "2-5% (B2B services average)",
        },
    }

    return report


def get_overall_analytics() -> Dict:
    """Get analytics across all campaigns."""
    campaigns = _load_campaigns()

    total_sent = 0
    total_replies = 0
    total_meetings = 0
    total_bounces = 0
    total_optouts = 0

    by_type = {}

    for c in campaigns:
        stats = c.get("stats", {})
        sent = stats.get("emails_sent", 0)
        total_sent += sent
        total_replies += stats.get("replies", 0)
        total_meetings += stats.get("meetings_booked", 0)
        total_bounces += stats.get("bounces", 0)
        total_optouts += stats.get("opt_outs", 0)

        etype = c.get("email_type", "unknown")
        if etype not in by_type:
            by_type[etype] = {"sent": 0, "replies": 0, "meetings": 0}
        by_type[etype]["sent"] += sent
        by_type[etype]["replies"] += stats.get("replies", 0)
        by_type[etype]["meetings"] += stats.get("meetings_booked", 0)

    safe_sent = max(total_sent, 1)

    return {
        "total_campaigns": len(campaigns),
        "active_campaigns": sum(1 for c in campaigns if c["status"] == "running"),
        "total_emails_sent": total_sent,
        "total_replies": total_replies,
        "total_meetings": total_meetings,
        "total_bounces": total_bounces,
        "total_opt_outs": total_optouts,
        "overall_reply_rate": f"{(total_replies / safe_sent * 100):.1f}%",
        "overall_meeting_rate": f"{(total_meetings / safe_sent * 100):.1f}%",
        "by_email_type": by_type,
    }


def get_send_log_summary(days: int = 7) -> Dict:
    """Get send log summary for the last N days."""
    daily_stats = {}

    for i in range(days):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = SEND_LOG_DIR / f"{day}.json"

        day_stats = {"sent": 0, "dry_run": 0, "skipped": 0, "errors": 0, "bounced": 0}

        if log_file.exists():
            with open(log_file, "r") as f:
                logs = json.load(f)
                for log in logs:
                    status = log.get("status", "error")
                    day_stats[status] = day_stats.get(status, 0) + 1

        daily_stats[day] = day_stats

    return {
        "period": f"Last {days} days",
        "daily": daily_stats,
        "total_sent": sum(d["sent"] for d in daily_stats.values()),
        "total_dry_run": sum(d["dry_run"] for d in daily_stats.values()),
    }


def sync_stats_from_logs() -> Dict:
    """
    Auto-sync campaign stats by scanning send logs, opens, and replies.
    Updates campaign records and returns a global summary.
    """
    # --- Gather all send logs ---
    all_logs = []
    if SEND_LOG_DIR.exists():
        for log_file in sorted(SEND_LOG_DIR.glob("*.json")):
            try:
                with open(log_file, "r") as f:
                    all_logs.extend(json.load(f))
            except Exception:
                pass

    # --- Gather open events ---
    opens_file = CAMPAIGNS_FILE.parent / "email_opens.json"
    opens = []
    if opens_file.exists():
        try:
            with open(opens_file, "r") as f:
                opens = json.load(f)
        except Exception:
            pass

    opened_send_ids = {o.get("send_id") for o in opens if o.get("send_id")}

    # --- Gather replies ---
    replies_file = CAMPAIGNS_FILE.parent / "replies.json"
    replies = []
    if replies_file.exists():
        try:
            with open(replies_file, "r") as f:
                replies = json.load(f)
        except Exception:
            pass

    reply_emails = {r.get("from_email", "").lower() for r in replies}

    # --- Compute global stats ---
    total_sent = 0
    total_bulk_sent = 0
    total_bounced = 0
    total_errors = 0
    total_opened = 0
    total_replied = 0

    for log in all_logs:
        status = log.get("status", "")
        if status == "sent":
            total_sent += 1
            if log.get("is_bulk"):
                total_bulk_sent += 1
            send_id = log.get("send_id", "")
            if send_id and send_id in opened_send_ids:
                total_opened += 1
            to_email = log.get("to_email", "").lower()
            if to_email and to_email in reply_emails:
                total_replied += 1
        elif status in ("bounced", "error"):
            total_bounced += 1

    # --- Update campaign stats if campaigns exist ---
    campaigns = _load_campaigns()
    for campaign in campaigns:
        campaign_id = campaign.get("id", "")
        campaign_logs = [l for l in all_logs if l.get("campaign_id") == campaign_id]
        campaign_sent = sum(1 for l in campaign_logs if l.get("status") == "sent")
        campaign_bounced = sum(1 for l in campaign_logs if l.get("status") in ("bounced", "error"))

        campaign_send_ids = {l.get("send_id") for l in campaign_logs if l.get("send_id")}
        campaign_opened = sum(1 for sid in campaign_send_ids if sid in opened_send_ids)

        campaign_to_emails = {l.get("to_email", "").lower() for l in campaign_logs if l.get("status") == "sent"}
        campaign_replied = sum(1 for em in campaign_to_emails if em in reply_emails)

        campaign["stats"]["emails_sent"] = campaign_sent
        campaign["stats"]["bounces"] = campaign_bounced
        campaign["stats"]["emails_opened"] = campaign_opened
        campaign["stats"]["replies"] = campaign_replied

    if campaigns:
        _save_campaigns(campaigns)

    safe_sent = max(total_sent, 1)

    return {
        "synced": True,
        "total_logs": len(all_logs),
        "total_sent": total_sent,
        "total_bulk_sent": total_bulk_sent,
        "total_bounced": total_bounced,
        "total_errors": total_errors,
        "total_opened": total_opened,
        "total_replied": total_replied,
        "open_rate": f"{(total_opened / safe_sent * 100):.1f}%",
        "reply_rate": f"{(total_replied / safe_sent * 100):.1f}%",
        "bounce_rate": f"{(total_bounced / safe_sent * 100):.1f}%",
    }
