"""
Neo Eco Cleaning — Content Calendar Generator
=================================================
Generate monthly content calendars for cleaning services B2B marketing.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent


# Pre-built content ideas by month/season — Cleaning Industry
CONTENT_IDEAS = {
    "January": [
        {"type": "LinkedIn Post", "topic": "New Year, New Cleaning Contracts — Capacity Announcement", "goal": "Awareness"},
        {"type": "Email Campaign", "topic": "2026 Block Cleaning Contracts — Early Bird Pricing", "goal": "Lead Gen"},
        {"type": "Case Study", "topic": "Rendall & Rittner — How we reduced tenant complaints by 90%", "goal": "Trust"},
        {"type": "Blog Post", "topic": "Block Cleaning Checklist for Property Managers", "goal": "SEO"},
    ],
    "February": [
        {"type": "LinkedIn Post", "topic": "Behind-the-scenes: Our eco-friendly cleaning products", "goal": "Trust"},
        {"type": "Email Campaign", "topic": "Spring Deep Clean Season — Book Your Properties Now", "goal": "Lead Gen"},
        {"type": "Blog Post", "topic": "How Often Should Block Cleaning Be Done? A Property Manager's Guide", "goal": "SEO"},
        {"type": "LinkedIn Post", "topic": "Meet our cleaning team — ex-Hilton Hotel professionals", "goal": "Credibility"},
    ],
    "March": [
        {"type": "Email Campaign", "topic": "Spring Deep Clean — Transform Your Communal Areas", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Before & After: Block cleaning transformation in Barnet", "goal": "Trust"},
        {"type": "Blog Post", "topic": "5 Questions to Ask Before Hiring a Block Cleaning Company", "goal": "SEO"},
        {"type": "LinkedIn Post", "topic": "Fire safety compliance: How clean communal areas save lives", "goal": "Authority"},
    ],
    "April": [
        {"type": "LinkedIn Post", "topic": "Spring is here — outdoor pressure washing season begins", "goal": "Awareness"},
        {"type": "Email Campaign", "topic": "Pressure Washing + Window Cleaning Bundle — Save 15%", "goal": "Lead Gen"},
        {"type": "Case Study", "topic": "MVN Block Management — Multi-site cleaning partnership", "goal": "Trust"},
        {"type": "Blog Post", "topic": "Eco-Friendly Cleaning: Why Toxic Chemicals Don't Belong in Communal Spaces", "goal": "SEO"},
    ],
    "May": [
        {"type": "LinkedIn Post", "topic": "Window cleaning showcase — before and after", "goal": "Awareness"},
        {"type": "Email Campaign", "topic": "Summer Cleaning Prep — Is Your Building Ready?", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Client testimonial spotlight: Property managers we work with", "goal": "Trust"},
        {"type": "Blog Post", "topic": "How to Choose a Block Cleaning Company in London", "goal": "SEO"},
    ],
    "June": [
        {"type": "Email Campaign", "topic": "Mid-Year Cleaning Contract Review — Free Assessment", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Summer Car Park pressure washing — keeping external areas pristine", "goal": "Awareness"},
        {"type": "Blog Post", "topic": "End of Tenancy Cleaning Checklist — What Letting Agents Expect", "goal": "SEO"},
        {"type": "LinkedIn Post", "topic": "Celebrating 6 months of 100% on-schedule cleans", "goal": "Trust"},
    ],
    "July": [
        {"type": "Email Campaign", "topic": "Summer Deep Clean — Book Before September Rush", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Summer doesn't stop cleaning — we work year-round", "goal": "Differentiation"},
        {"type": "Case Study", "topic": "Victoria Wharf — Emergency COVID-safe deep cleaning", "goal": "Trust"},
        {"type": "Blog Post", "topic": "Property Management Cleaning: The Complete Guide", "goal": "SEO"},
    ],
    "August": [
        {"type": "LinkedIn Post", "topic": "Back-to-routine: September cleaning schedules filling fast", "goal": "Urgency"},
        {"type": "Email Campaign", "topic": "Q4 Cleaning Contracts — Secure Your Preferred Schedule", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Our eco-friendly commitment: Products we use and why", "goal": "CSR"},
        {"type": "Blog Post", "topic": "Stairwell Cleaning Best Practices for Residential Blocks", "goal": "SEO"},
    ],
    "September": [
        {"type": "Email Campaign", "topic": "Autumn Prep — External Cleaning Before Winter Sets In", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Autumn leaf clearance and pathway cleaning for your properties", "goal": "Seasonal"},
        {"type": "Blog Post", "topic": "Fire Safety and Cleaning: Keeping Communal Areas Compliant", "goal": "SEO"},
        {"type": "LinkedIn Post", "topic": "Meet our team: Quality assurance and inspection process", "goal": "Trust"},
    ],
    "October": [
        {"type": "Email Campaign", "topic": "New Year, New Cleaner? — Start Planning Your 2027 Contract", "goal": "Lead Gen"},
        {"type": "LinkedIn Post", "topic": "Pre-winter pressure washing — car parks and pathways", "goal": "Seasonal"},
        {"type": "Case Study", "topic": "How switching to eco-cleaning improved tenant satisfaction", "goal": "Trust"},
        {"type": "Blog Post", "topic": "Communal Area Cleaning Standards: What Leaseholders Expect", "goal": "SEO"},
    ],
    "November": [
        {"type": "Email Campaign", "topic": "End of Year Capacity — Priority Q1 2027 Cleaning Slots", "goal": "Urgency"},
        {"type": "LinkedIn Post", "topic": "Our focus: Quality over speed — cleaning done right", "goal": "Brand"},
        {"type": "LinkedIn Post", "topic": "Year in review — properties cleaned, clients served, standards maintained", "goal": "Trust"},
        {"type": "Blog Post", "topic": "Planning Your 2027 Property Cleaning Budget: A Manager's Guide", "goal": "SEO"},
    ],
    "December": [
        {"type": "LinkedIn Post", "topic": "Thank you to all our property management partners — year in review", "goal": "Relationship"},
        {"type": "Email Campaign", "topic": "2027 Block Cleaning Partnerships — Book a January Consultation", "goal": "Lead Gen"},
        {"type": "Blog Post", "topic": "Cleaning Trends for Property Managers in 2027", "goal": "Thought Leadership"},
        {"type": "LinkedIn Post", "topic": "Holiday message + January cleaning restart dates", "goal": "Communication"},
    ],
}


def generate_monthly_calendar(month: str = None, year: int = None) -> Dict:
    """Generate a content calendar for a specific month."""
    if not month:
        month = datetime.now().strftime("%B")
    if not year:
        year = datetime.now().year

    ideas = CONTENT_IDEAS.get(month, CONTENT_IDEAS.get("January"))

    calendar = {
        "month": month,
        "year": year,
        "generated_at": datetime.now().isoformat(),
        "content_items": [],
    }

    for i, idea in enumerate(ideas):
        week = i + 1
        item = {
            "week": week,
            "estimated_date": f"Week {week} of {month}",
            "content_type": idea["type"],
            "topic": idea["topic"],
            "goal": idea["goal"],
            "status": "planned",
            "notes": "",
        }
        calendar["content_items"].append(item)

    return calendar


def generate_quarterly_calendar(quarter: int = None) -> Dict:
    """Generate a 3-month content calendar."""
    if quarter is None:
        quarter = (datetime.now().month - 1) // 3 + 1

    months_map = {
        1: ["January", "February", "March"],
        2: ["April", "May", "June"],
        3: ["July", "August", "September"],
        4: ["October", "November", "December"],
    }

    months = months_map.get(quarter, months_map[1])
    year = datetime.now().year

    return {
        "quarter": f"Q{quarter} {year}",
        "months": [generate_monthly_calendar(m, year) for m in months],
        "total_items": sum(
            len(generate_monthly_calendar(m, year)["content_items"])
            for m in months
        ),
    }


def export_calendar_markdown(calendar: Dict) -> str:
    """Export calendar as Markdown."""
    lines = [
        f"# Content Calendar — {calendar.get('month', calendar.get('quarter', ''))} {calendar.get('year', '')}",
        "",
        f"*Generated: {datetime.now().strftime('%d %B %Y')}*",
        "",
    ]

    if "months" in calendar:
        for month_cal in calendar["months"]:
            lines.append(f"## {month_cal['month']}")
            lines.append("")
            lines.append("| Week | Type | Topic | Goal | Status |")
            lines.append("|------|------|-------|------|--------|")
            for item in month_cal["content_items"]:
                lines.append(
                    f"| {item['week']} | {item['content_type']} | "
                    f"{item['topic']} | {item['goal']} | {item['status']} |"
                )
            lines.append("")
    else:
        lines.append("| Week | Type | Topic | Goal | Status |")
        lines.append("|------|------|-------|------|--------|")
        for item in calendar.get("content_items", []):
            lines.append(
                f"| {item['week']} | {item['content_type']} | "
                f"{item['topic']} | {item['goal']} | {item['status']} |"
            )

    return "\n".join(lines)
