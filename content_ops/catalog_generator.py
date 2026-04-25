"""
Neo Eco Cleaning — Service Catalog Generator
================================================
Generate beautifully formatted service catalog content from the services database.
Supports Markdown and HTML output.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from tz_utils import now_ist
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = BASE_DIR / "data" / "products.json"
OUTPUT_DIR = BASE_DIR / "output" / "catalogs"


def _load_products() -> List[Dict]:
    if PRODUCTS_FILE.exists():
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("products", data) if isinstance(data, dict) else data
    return []


def generate_product_description(product: Dict, style: str = "b2b") -> str:
    """Generate a service description from data."""
    eco = ", ".join(product.get("fabrics", [])[:3])
    certs = ", ".join(product.get("certifications", []))
    options = ", ".join(product.get("customization", [])[:3])

    return (
        f"{product.get('description', product.get('name', 'Professional cleaning service'))}. "
        f"Eco features: {eco}. "
        f"Certified: {certs}. "
        f"Options: {options}. "
        f"Pricing: {product.get('pricing_range_gbp', product.get('price_range_usd', 'Contact for quote'))}."
    )


def generate_catalog_markdown(
    title: str = "Neo Eco Cleaning — Service Catalog 2026",
    products: List[Dict] = None,
) -> str:
    """Generate a full service catalog in Markdown format."""
    if products is None:
        products = _load_products()

    lines = [
        f"# {title}",
        "",
        f"*Generated: {now_ist().strftime('%B %Y')}*",
        "",
        "---",
        "",
        "## Why Choose Neo Eco Cleaning?",
        "",
        "- **100% Eco-Friendly** — All-natural cleaning products, no toxic chemicals",
        "- **50+ Years Experience** — Combined team expertise across all cleaning disciplines",
        "- **Ex-Hilton Hotel Staff** — Hospitality-grade cleaning standards",
        "- **Quality Guarantee** — All complaints resolved at no additional cost",
        "- **Award-Winning Clients** — Trusted by Rendall & Rittner (PM of the Year 2024)",
        "- **North London Specialists** — Dedicated local teams, fast response times",
        "- **Free Site Survey** — No-obligation assessment within 48 hours",
        "",
        "---",
        "",
    ]

    # Group by category
    categories = {}
    for p in products:
        cat = p.get("category", "Other")
        categories.setdefault(cat, []).append(p)

    for cat_name, cat_products in categories.items():
        lines.append(f"## {cat_name}")
        lines.append("")

        for product in cat_products:
            lines.append(f"### {product.get('name', 'Service')}")
            lines.append("")
            lines.append(f"**Service ID:** {product.get('id', 'N/A')}")
            lines.append("")

            desc = generate_product_description(product)
            lines.append(desc)
            lines.append("")

            lines.append("| Detail | Information |")
            lines.append("|--------|------------|")
            lines.append(f"| **Pricing** | {product.get('pricing_range_gbp', product.get('price_range_usd', 'Contact us'))} |")
            lines.append(f"| **Response Time** | {product.get('lead_time_days', 'N/A')} days |")
            lines.append(f"| **Eco Features** | {', '.join(product.get('fabrics', []))} |")
            lines.append(f"| **Certifications** | {', '.join(product.get('certifications', []))} |")
            lines.append(f"| **Coverage** | {', '.join(product.get('sizes', [])) if isinstance(product.get('sizes'), list) else product.get('sizes', 'All areas')} |")
            lines.append(f"| **Options** | {', '.join(product.get('customization', []))} |")
            lines.append("")
            lines.append("---")
            lines.append("")

    lines.extend([
        "## Get Started",
        "",
        "Ready to discuss your cleaning requirements?",
        "",
        "- 📧 Email: priyanka.singh@neoecocleaning.co.uk",
        "- 📞 Phone: +44 (0) 77680 66860",
        "- 🌐 Website: neoecocleaning.co.uk",
        "- 📋 Request a free site survey — no obligation",
        "",
        "*All prices exclude VAT. Custom quotes available for multi-site contracts.*",
        "",
    ])

    return "\n".join(lines)


def generate_catalog_html(title: str = "Neo Eco Cleaning — Service Catalog 2026") -> str:
    """Generate a styled HTML catalog."""
    products = _load_products()
    md_content = generate_catalog_markdown(title, products)

    import re
    html_body = md_content
    html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
    html_body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)
    html_body = re.sub(r'^- (.+)$', r'<li>\1</li>', html_body, flags=re.MULTILINE)
    html_body = html_body.replace("---", "<hr/>")
    html_body = re.sub(r'\n\n', '</p><p>', html_body)
    html_body = f"<p>{html_body}</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto;
         padding: 40px 20px; color: #1a1a2e; line-height: 1.7; background: #fafafa; }}
  h1 {{ color: #065f46; border-bottom: 3px solid #059669; padding-bottom: 12px; }}
  h2 {{ color: #059669; margin-top: 40px; }}
  h3 {{ color: #047857; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th, td {{ padding: 10px 14px; border: 1px solid #ddd; text-align: left; }}
  th {{ background: #059669; color: white; }}
  tr:nth-child(even) {{ background: #f0fdf4; }}
  hr {{ border: none; border-top: 2px solid #e0e0e0; margin: 30px 0; }}
  li {{ margin: 4px 0; }}
  strong {{ color: #065f46; }}
</style>
</head>
<body>{html_body}</body>
</html>"""


def save_catalog(format: str = "markdown") -> str:
    """Generate and save catalog to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = now_ist().strftime("%Y%m%d")

    if format == "html":
        content = generate_catalog_html()
        filepath = OUTPUT_DIR / f"neo_eco_catalog_{timestamp}.html"
    else:
        content = generate_catalog_markdown()
        filepath = OUTPUT_DIR / f"neo_eco_catalog_{timestamp}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return str(filepath)
