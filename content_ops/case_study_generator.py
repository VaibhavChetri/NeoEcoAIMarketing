"""
Neo Eco Cleaning — Case Study Generator
==========================================
Create professional B2B case studies from structured input.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CASE_STUDIES_FILE = BASE_DIR / "data" / "case_studies.json"
OUTPUT_DIR = BASE_DIR / "output" / "case_studies"


def _load_case_studies():
    if CASE_STUDIES_FILE.exists():
        with open(CASE_STUDIES_FILE, "r") as f:
            return json.load(f)
    return []


def _save_case_study(case_study: Dict):
    studies = _load_case_studies()
    studies.append(case_study)
    CASE_STUDIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CASE_STUDIES_FILE, "w") as f:
        json.dump(studies, f, indent=2, ensure_ascii=False)


def create_case_study(
    client_name: str,
    industry: str,
    country: str,
    challenge: str,
    solution: str,
    results: Dict,
    testimonial: str = "",
    title: str = "",
) -> Dict:
    """Create a new case study and save it."""
    case_study = {
        "id": f"cs-{datetime.now().strftime('%Y%m%d%H%M')}",
        "title": title or f"{country} {industry} — {client_name}",
        "client": client_name,
        "industry": industry,
        "country": country,
        "challenge": challenge,
        "solution": solution,
        "results": results,
        "testimonial": testimonial,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }

    _save_case_study(case_study)
    return case_study


def generate_case_study_markdown(case_study: Dict) -> str:
    """Generate a Markdown-formatted case study."""
    results = case_study.get("results", {})

    lines = [
        f"# Case Study: {case_study.get('title', '')}",
        "",
        f"**Client:** {case_study.get('client', '')}",
        f"**Industry:** {case_study.get('industry', '')}",
        f"**Area:** {case_study.get('country', '')}",
        "",
        "---",
        "",
        "## The Challenge",
        "",
        case_study.get("challenge", ""),
        "",
        "## Our Solution",
        "",
        case_study.get("solution", ""),
        "",
        "## Results",
        "",
    ]

    if results:
        lines.append("| Metric | Result |")
        lines.append("|--------|--------|")
        result_labels = {
            "cost_savings": "💰 Cost Savings",
            "delivery": "📦 Reliability",
            "quality": "✅ Quality",
            "reorder": "🔄 Contract Renewal",
        }
        for key, value in results.items():
            label = result_labels.get(key, key.replace("_", " ").title())
            lines.append(f"| {label} | {value} |")
        lines.append("")

    if case_study.get("testimonial"):
        lines.extend([
            "## Client Testimonial",
            "",
            f"> *\"{case_study['testimonial']}\"*",
            "",
        ])

    lines.extend([
        "---",
        "",
        "**Ready to achieve similar results?** Contact Neo Eco Cleaning today.",
        "📧 priyanka.singh@neoecocleaning.co.uk | 📞 +44 (0) 77680 66860",
    ])

    return "\n".join(lines)


def save_case_study_file(case_study: Dict, format: str = "markdown") -> str:
    """Save a case study to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    slug = case_study.get("title", "case_study").lower()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = slug.strip().replace(" ", "_")[:50]

    if format == "markdown":
        content = generate_case_study_markdown(case_study)
        filepath = OUTPUT_DIR / f"{slug}.md"
    else:
        content = json.dumps(case_study, indent=2)
        filepath = OUTPUT_DIR / f"{slug}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return str(filepath)


def list_case_studies() -> list:
    """List all available case studies."""
    return _load_case_studies()
