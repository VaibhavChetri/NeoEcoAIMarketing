#!/usr/bin/env python3
"""
Resend Failed Emails — One-time script
=======================================
Resends the 15 emails that failed due to Zoho rate limiting & syntax errors.
Includes initial cooldown wait and retry logic with exponential backoff.
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from tz_utils import now_ist

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from outbound_engine.email_sender import send_email_async, DELAY_SECONDS, DRY_RUN


# All 15 failed emails extracted from send logs (2026-04-15.json)
FAILED_EMAILS = [
    {
        "to_email": "jessica@jpropertymanagement.co.uk",
        "subject": "Eco-Friendly Cleaning for Your North London Properties",
        "body": "Hi Jessica,\n\nWe understand that managing properties across North London means ensuring impeccable standards and reliable service, which is exactly what we excel at.\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products - no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff - hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee - all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning - weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning - from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nPressure Washing - from \u00a3250/session, for driveways, car parks, and building exteriors.\n\nWindow Cleaning - from \u00a3100/session, internal and external options available.\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote - completely free.",
        "lead_id": "c98faabc",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "arshi@grange.london",
        "subject": "Grange London Limited \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi Arshi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "4fbf58fc",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "jayne@brixlondon.com",
        "subject": "Brix London \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi Jayne,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "9fe73771",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "filip@premierlondonproperty.co.uk",
        "subject": "Premier London Property Limited \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi Filip,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "9e083db8",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "team@fandcoproperty.com",
        "subject": "F and Co Property Group \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "966d2375",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "hussam@doubleelevenmanagement.com",
        "subject": "Double Eleven Management ltd \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi Hussam,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "6f0186f5",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "info@mbrpropertymanagement.co.uk",
        "subject": "Unico Property Management Ltd \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "1cd50672",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "info@unicoproperty.co.uk",
        "subject": "Eco-Friendly Cleaning for ION Property Management - Trusted by Award-Winners",
        "body": "Hi,\n\nWe understand that as a property management company in the UK, maintaining pristine and healthy environments for your residents and tenants is a top priority.\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products - no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff - hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee - all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning - weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Deep Clean - from \u00a3180/property, 24-hour turnaround, meets letting agent standards.\n\nCommercial Office Cleaning - daily, 3x weekly, or weekly cleaning from \u00a3200/month, ensuring a spotless workspace.\n\nPressure Washing Service - from \u00a3250/session for driveways, car parks, and building exteriors.\n\nWindow Cleaning Service - internal and external options from \u00a3100/session for streak-free views.\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote - completely free.",
        "lead_id": "236291c2",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "enquiries@homeworldmanagement.co.uk",
        "subject": "Home World Management Ltd \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "ea5d57c4",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "kensingtonproperty2000@gmail.com",
        "subject": "Kensington Property Management \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "68f7d8ac",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "abbe@mihproperty.co.uk",
        "subject": "MIH Property Management Ltd \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "dff79e11",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "andrew.selwyn@ringley.co.uk",
        "subject": "Ringley Limited \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi Andrew,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "675e939d",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "info@hartswoodproperty.co.uk",
        "subject": "Hartswood Lettings & Property Management \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "b7935b33",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "info@gorepropertymanagement.com",
        "subject": "Gore Property Management \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "1bb6770f",
        "campaign_id": "campaign_20260415_132430"
    },
    {
        "to_email": "info@diakoproperty.co.uk",
        "subject": "Diako property management Ltd \u2014 Eco-Friendly Block Cleaning for Your Properties",
        "body": "Hi,\n\nMany property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:\n\n\u2022 100% eco-friendly cleaning products \u2014 no toxic chemicals in shared spaces\n\n\u2022 Ex-Hilton Hotel trained staff \u2014 hospitality-grade cleaning standards\n\n\u2022 Quality Guarantee \u2014 all complaints resolved at no additional cost\n\n\u2022 Trusted by Rendall & Rittner (Property Manager of the Year 2024), MVN Block Management and many estate agents.\n\nBased on your portfolio, we think these services could be particularly relevant:\n\nBlock & Communal Cleaning \u2014 weekly scheduled cleans from \u00a3150/month, includes stairwells, lobbies, and bin rooms.\n\nEnd of Tenancy Cleaning \u2014 from \u00a3180/property, 24-hour turnaround, meets letting agent standards\n\nProfessional Carpet Cleaning - from \u00a3200 onwards\n\nJetwashing/ Pressure Washing - from \u00a3100 onwards\n\nGutter Cleaning - from \u00a3200 onwards\n\nWe work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.\n\nWould a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote \u2014 completely free.",
        "lead_id": "88acb264",
        "campaign_id": "campaign_20260415_132430"
    }
]


# Track progress in a file so we can resume if interrupted
PROGRESS_FILE = BASE_DIR / "output" / "resend_progress.json"


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"sent": [], "errors": [], "pending_from_index": 0}


def save_progress(progress):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2, default=str)


async def resend_failed():
    # Use 90-second delay between emails (more conservative than 60s)
    delay = max(DELAY_SECONDS, 90)
    
    progress = load_progress()
    start_from = progress["pending_from_index"]
    
    remaining = FAILED_EMAILS[start_from:]
    total = len(FAILED_EMAILS)
    
    print(f"\n{'='*60}")
    print(f"  RESENDING FAILED EMAILS")
    print(f"  Total: {total} | Already done: {start_from} | Remaining: {len(remaining)}")
    print(f"  Delay between emails: {delay}s")
    print(f"  DRY_RUN: {DRY_RUN}")
    print(f"  Time: {now_ist().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    if not remaining:
        print("  ✅ All emails already sent! Nothing to do.")
        return

    # Test if Zoho is still blocking with first email
    consecutive_errors = 0
    max_consecutive_errors = 3  # If 3 in a row fail, Zoho is still blocking

    for i, email_data in enumerate(remaining):
        idx = start_from + i
        to = email_data["to_email"]
        print(f"  [{idx+1}/{total}] Sending to {to}...", end=" ", flush=True)

        result = await send_email_async(
            to_email=to,
            subject=email_data["subject"],
            body=email_data["body"],
            lead_id=email_data["lead_id"],
            campaign_id=email_data["campaign_id"],
            is_bulk=True,
        )

        status = result.get("status", "error")
        if status == "sent":
            consecutive_errors = 0
            progress["sent"].append(to)
            progress["pending_from_index"] = idx + 1
            save_progress(progress)
            print("✅ SENT")
        elif status == "dry_run":
            consecutive_errors = 0
            progress["sent"].append(to)
            progress["pending_from_index"] = idx + 1
            save_progress(progress)
            print("🟡 DRY RUN")
        else:
            consecutive_errors += 1
            error_msg = result.get('error', 'Unknown')
            progress["errors"].append({"email": to, "error": error_msg, "time": now_ist().isoformat()})
            save_progress(progress)
            print(f"❌ ERROR: {error_msg}")

            if consecutive_errors >= max_consecutive_errors:
                print(f"\n  ⚠️  {max_consecutive_errors} consecutive errors — Zoho rate limit still active!")
                print(f"  ⏸️  Pausing. Progress saved at email #{idx+1}.")
                print(f"  📋 Run this script again in 30-60 minutes to resume from where we left off.")
                print(f"     Progress file: {PROGRESS_FILE}")
                return

        # Rate limiting
        if i < len(remaining) - 1:
            print(f"        ⏳ Waiting {delay}s before next send...")
            await asyncio.sleep(delay)

    print(f"\n{'='*60}")
    print(f"  COMPLETE!")
    print(f"  Sent: {len(progress['sent'])}")
    print(f"  Errors: {len(progress['errors'])}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(resend_failed())
