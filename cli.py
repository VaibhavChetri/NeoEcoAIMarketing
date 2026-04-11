#!/usr/bin/env python3
"""
Neo Eco Cleaning — AI Marketing Skills CLI
============================================
Command-line interface for all marketing tools.

Usage:
  python cli.py leads import
  python cli.py leads list --country "North London"
  python cli.py email generate --lead-id <id> --type cold_outreach
  python cli.py pipeline view
  python cli.py content catalog
  python cli.py dashboard
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    import click

console = Console() if HAS_RICH else None

def print_header(title):
    if console:
        console.print(Panel(f"[bold cyan]{title}[/]", border_style="cyan", box=box.ROUNDED))
    else:
        print(f"\n{'='*60}\n  {title}\n{'='*60}\n")


@click.group()
def cli():
    """🧹 Neo Eco Cleaning — AI Marketing Skills Toolkit"""
    pass


# ═══════════════════════════════════════════════════════════════
#  LEADS
# ═══════════════════════════════════════════════════════════════

@cli.group()
def leads():
    """👥 Manage leads"""
    pass


@leads.command("import")
@click.option("--csv", default="", help="Path to CSV file")
def leads_import(csv):
    """Import leads from CSV/Excel"""
    print_header("Import Leads")
    from outbound_engine.lead_manager import import_leads_file

    if not csv:
        csv = str(BASE_DIR / "Email_Upload_Template.xlsx")

    result = import_leads_file(csv)

    if "error" in result:
        click.echo(f"❌ {result['error']}")
        return

    click.echo(f"✅ Imported: {result['total_imported']} new leads")
    click.echo(f"📊 Total in database: {result['total_in_database']}")


@leads.command("list")
@click.option("--country", default=None, help="Filter by country/area")
@click.option("--stage", default=None, help="Filter by stage")
@click.option("--industry", default=None, help="Filter by industry")
@click.option("--query", default=None, help="Search term")
@click.option("--limit", default=20, help="Max results to show")
def leads_list(country, stage, industry, query, limit):
    """List and filter leads"""
    from outbound_engine.lead_manager import search_leads

    results = search_leads(country=country, stage=stage, industry=industry, query=query)

    if console:
        table = Table(title=f"Leads ({len(results)} found)", box=box.ROUNDED, border_style="dim")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Company", style="bold white", max_width=25)
        table.add_column("Area", width=16)
        table.add_column("Industry", width=18)
        table.add_column("Employees", width=10, justify="right")
        table.add_column("Stage", width=12)
        table.add_column("Email?", width=6, justify="center")

        for lead in results[:limit]:
            has_email = "✅" if any(c.get("email") for c in lead.get("contacts", [])) else "❌"
            stage_color = {
                "new": "blue", "contacted": "magenta", "replied": "cyan",
                "meeting_booked": "yellow", "won": "green", "lost": "red",
            }.get(lead.get("stage", "new"), "white")

            table.add_row(
                lead["id"][:8],
                lead["company_name"],
                lead.get("country", "N/A"),
                lead.get("industry", "N/A"),
                str(lead.get("employees", "-")),
                f"[{stage_color}]{lead.get('stage', 'new')}[/{stage_color}]",
                has_email,
            )

        console.print(table)
    else:
        for lead in results[:limit]:
            click.echo(f"  {lead['id'][:8]}  {lead['company_name']:<25}  {lead.get('country', 'N/A'):<16}  {lead.get('stage', 'new')}")

    if len(results) > limit:
        click.echo(f"\n  ... and {len(results) - limit} more (use --limit to show more)")


@leads.command("stats")
def leads_stats():
    """Show pipeline statistics"""
    print_header("Pipeline Statistics")
    from outbound_engine.lead_manager import get_pipeline_stats

    stats = get_pipeline_stats()

    click.echo(f"  📊 Total Leads: {stats['total_leads']}")
    click.echo(f"  📧 With Email: {stats['with_email']}")
    click.echo(f"  👤 With Contacts: {stats['with_contacts']}")
    click.echo()

    click.echo("  🔄 By Stage:")
    for stage, count in stats["by_stage"].items():
        if count > 0:
            bar = "█" * count + "░" * (20 - min(count, 20))
            click.echo(f"    {stage:<16} {bar} {count}")

    click.echo()
    click.echo("  🌍 By Area:")
    for country, count in list(stats["by_country"].items())[:10]:
        if count > 0:
            click.echo(f"    {country:<20} {count}")


# ═══════════════════════════════════════════════════════════════
#  EMAIL
# ═══════════════════════════════════════════════════════════════

@cli.group()
def email():
    """📧 Generate and send emails"""
    pass


@email.command("generate")
@click.option("--lead-id", required=True, help="Lead ID to generate email for")
@click.option("--type", "email_type", default="cold_outreach",
              type=click.Choice(["cold_outreach", "follow_up_case_study", "follow_up_quote", "breakup"]))
def email_generate(lead_id, email_type):
    """Generate a personalized email for a lead"""
    print_header("Generate Email")
    from outbound_engine.lead_manager import get_lead
    from outbound_engine.email_generator import generate_email, score_email

    lead = get_lead(lead_id)
    if not lead:
        click.echo(f"❌ Lead not found: {lead_id}")
        return

    click.echo(f"  🏢 Company: {lead['company_name']}")
    click.echo(f"  📧 Type: {email_type}")
    click.echo(f"  ⏳ Generating...")

    result = generate_email(lead, email_type)
    quality = score_email(result)

    click.echo(f"\n  📧 Subject: {result['subject']}")
    click.echo(f"\n  {'─'*50}")
    click.echo(f"  {result['body']}")
    click.echo(f"  {'─'*50}")
    click.echo(f"\n  📊 Quality Score: {quality['overall']}/100")
    click.echo(f"  🤖 {'AI Generated' if result.get('ai_generated') else 'Template Based'}")


@email.command("generate-batch")
@click.option("--country", default=None, help="Filter leads by area")
@click.option("--stage", default="new", help="Filter leads by stage")
@click.option("--type", "email_type", default="cold_outreach")
@click.option("--limit", default=10, help="Max emails to generate")
def email_generate_batch(country, stage, email_type, limit):
    """Generate emails for multiple leads"""
    print_header("Batch Email Generation")
    from outbound_engine.lead_manager import search_leads
    from outbound_engine.email_generator import generate_campaign_emails

    leads = search_leads(country=country, stage=stage)[:limit]
    click.echo(f"  Found {len(leads)} leads matching criteria")

    if not leads:
        click.echo("  ❌ No leads found")
        return

    emails = generate_campaign_emails(leads, email_type)
    click.echo(f"\n  ✅ Generated {len(emails)} emails")


# ═══════════════════════════════════════════════════════════════
#  PIPELINE
# ═══════════════════════════════════════════════════════════════

@cli.group()
def pipeline():
    """🎯 Sales pipeline management"""
    pass


@pipeline.command("view")
def pipeline_view():
    """View pipeline overview"""
    print_header("Sales Pipeline")
    from outbound_engine.lead_manager import get_pipeline_stats

    stats = get_pipeline_stats()
    stages_order = ["new", "contacted", "replied", "meeting_booked", "negotiation", "won", "lost"]

    if console:
        table = Table(title="Pipeline Overview", box=box.ROUNDED, border_style="dim")
        table.add_column("Stage", style="bold", width=18)
        table.add_column("Count", justify="right", width=8)
        table.add_column("Progress", width=30)

        total = max(stats["total_leads"], 1)
        for stage in stages_order:
            count = stats["by_stage"].get(stage, 0)
            pct = count / total * 100
            bar = "█" * int(pct / 5)
            color = {"won": "green", "lost": "red", "meeting_booked": "yellow",
                     "negotiation": "yellow", "replied": "cyan"}.get(stage, "magenta")
            table.add_row(stage.replace("_", " ").title(), str(count),
                         f"[{color}]{bar}[/{color}] {pct:.0f}%")

        console.print(table)
    else:
        for stage in stages_order:
            count = stats["by_stage"].get(stage, 0)
            click.echo(f"  {stage:<18} {count}")


# ═══════════════════════════════════════════════════════════════
#  SCORING
# ═══════════════════════════════════════════════════════════════

@cli.command()
@click.option("--limit", default=15, help="Top N leads to show")
def scoring(limit):
    """⭐ Score leads by ICP match"""
    print_header("Lead Scoring")
    from outbound_engine.lead_manager import get_all_leads
    from sales_pipeline.lead_scorer import score_all_leads

    leads = get_all_leads()
    scored = score_all_leads(leads)[:limit]

    if console:
        table = Table(title=f"Top {limit} Leads by ICP Score", box=box.ROUNDED, border_style="dim")
        table.add_column("Company", style="bold white", max_width=25)
        table.add_column("Area", width=16)
        table.add_column("Score", justify="right", width=7)
        table.add_column("Grade", width=6, justify="center")
        table.add_column("Recommendation", max_width=30)

        for s in scored:
            color = {"A": "green", "B": "blue", "C": "yellow", "D": "red"}.get(s["grade"], "white")
            table.add_row(
                s["company_name"], s.get("country", "N/A"),
                f"[{color}]{s['overall']}[/{color}]",
                f"[{color}]{s['grade']}[/{color}]",
                s.get("recommendation", ""),
            )
        console.print(table)
    else:
        for s in scored:
            click.echo(f"  {s['overall']:>5.1f}  [{s['grade']}]  {s['company_name']:<25}  {s.get('country', '')}")


# ═══════════════════════════════════════════════════════════════
#  CONTENT
# ═══════════════════════════════════════════════════════════════

@cli.group()
def content():
    """📝 Content generation tools"""
    pass


@content.command("catalog")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "html"]))
@click.option("--save/--no-save", default=False)
def content_catalog(fmt, save):
    """Generate service catalog"""
    print_header("Service Catalog")
    from content_ops.catalog_generator import generate_catalog_markdown, save_catalog

    if save:
        filepath = save_catalog(format=fmt)
        click.echo(f"  ✅ Catalog saved to: {filepath}")
    else:
        content = generate_catalog_markdown()
        click.echo(content)


@content.command("calendar")
@click.option("--month", default=None, help="Month name (e.g., April)")
@click.option("--quarter", default=None, type=int, help="Quarter (1-4)")
def content_calendar(month, quarter):
    """Generate content calendar"""
    print_header("Content Calendar")
    from content_ops.content_calendar import generate_monthly_calendar, generate_quarterly_calendar, export_calendar_markdown

    if quarter:
        cal = generate_quarterly_calendar(quarter)
    else:
        cal = generate_monthly_calendar(month)

    click.echo(export_calendar_markdown(cal))


@content.command("case-studies")
def content_case_studies():
    """List case studies"""
    print_header("Case Studies")
    from content_ops.case_study_generator import list_case_studies

    studies = list_case_studies()
    for cs in studies:
        click.echo(f"\n  📋 {cs['title']}")
        click.echo(f"     Client: {cs.get('client', 'N/A')} | Area: {cs.get('country', 'N/A')}")
        results = cs.get("results", {})
        for k, v in results.items():
            click.echo(f"     {k}: {v}")


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════

@cli.command()
@click.option("--port", default=8001, help="Dashboard port")
def dashboard(port):
    """🌐 Start the web dashboard"""
    print_header("Starting Dashboard")
    click.echo(f"  🚀 Dashboard: http://127.0.0.1:{port}")
    click.echo(f"  📚 API Docs: http://127.0.0.1:{port}/docs")
    click.echo(f"  Press Ctrl+C to stop\n")

    import uvicorn
    sys.path.insert(0, str(BASE_DIR / "dashboard"))
    uvicorn.run("dashboard.app:app", host="127.0.0.1", port=port, reload=True)


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    cli()
