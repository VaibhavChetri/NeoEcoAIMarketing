"""
Neo Eco Cleaning — AI Marketing Dashboard
=========================================
FastAPI-powered web dashboard for managing leads, campaigns, content, and pipeline.
Now with Apollo search, email upload, Gemini-powered bulk email generation, and sending.
"""

import sys
import json
import csv
import io
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Query, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from dotenv import load_dotenv
import asyncio

# Add parent to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env", override=True)

KEEP_ALIVE_URL = "https://neoecoaimarketing.onrender.com/health"
KEEP_ALIVE_INTERVAL = 14 * 60  # 14 minutes in seconds


async def _keep_alive_pinger():
    """Ping /health every 14 minutes to prevent Render free-tier spin-down."""
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            try:
                resp = await client.get(KEEP_ALIVE_URL)
                print(f"[keep-alive] pinged {KEEP_ALIVE_URL} → {resp.status_code}")
            except Exception as e:
                print(f"[keep-alive] ping failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage background tasks on startup/shutdown."""
    # Start background tasks
    keep_alive_task = asyncio.create_task(_keep_alive_pinger())
    reply_scanner_task = asyncio.create_task(_background_reply_scanner())
    print("[startup] Background tasks started (keep-alive + reply scanner)")
    yield
    # Cancel background tasks on shutdown
    keep_alive_task.cancel()
    reply_scanner_task.cancel()
    print("[shutdown] Background tasks cancelled")


app = FastAPI(
    title="Neo Eco Cleaning — AI Marketing Dashboard",
    description="B2C/B2B Outbound Engine for Eco-Friendly Cleaning Services",
    version="2.0.0",
    lifespan=lifespan,
)

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Generated emails storage
GENERATED_EMAILS_FILE = BASE_DIR / "output" / "generated_emails.json"


def _load_generated_emails():
    if GENERATED_EMAILS_FILE.exists():
        with open(GENERATED_EMAILS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_generated_emails(emails):
    GENERATED_EMAILS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GENERATED_EMAILS_FILE, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False, default=str)


# ─── Root: Serve Dashboard ───────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard loading...</h1>")


# ─── Health Check (keep-alive target for Render) ─────────────
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════
#  LEADS API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/leads")
async def api_get_leads(
    country: Optional[str] = None,
    industry: Optional[str] = None,
    stage: Optional[str] = None,
    query: Optional[str] = None,
    has_email: Optional[bool] = None,
):
    from outbound_engine.lead_manager import search_leads, get_all_leads
    if any([country, industry, stage, query, has_email is not None]):
        leads = search_leads(country=country, industry=industry, stage=stage,
                            query=query, has_email=has_email)
    else:
        leads = get_all_leads()
    return {"leads": leads, "count": len(leads)}


@app.get("/api/leads/{lead_id}")
async def api_get_lead(lead_id: str):
    from outbound_engine.lead_manager import get_lead
    lead = get_lead(lead_id)
    if lead:
        return lead
    return JSONResponse(status_code=404, content={"error": "Lead not found"})


@app.post("/api/leads/import")
async def api_import_leads(request: Request):
    body = await request.json()
    file_path = body.get("file_path", body.get("csv_path", ""))
    if not file_path:
        file_path = str(BASE_DIR / "Email_Upload_Template.xlsx")
    from outbound_engine.lead_manager import import_leads_file
    result = import_leads_file(file_path)
    return result


@app.post("/api/leads/{lead_id}/stage")
async def api_update_stage(lead_id: str, request: Request):
    body = await request.json()
    from outbound_engine.lead_manager import update_lead_stage
    success = update_lead_stage(lead_id, body.get("stage", ""), body.get("note", ""))
    return {"success": success}


@app.post("/api/leads/{lead_id}/note")
async def api_add_note(lead_id: str, request: Request):
    body = await request.json()
    from outbound_engine.lead_manager import add_note
    success = add_note(lead_id, body.get("note", ""))
    return {"success": success}


@app.get("/api/leads/stats/pipeline")
async def api_pipeline_stats():
    from outbound_engine.lead_manager import get_pipeline_stats
    return get_pipeline_stats()


# ═══════════════════════════════════════════════════════════════
#  APOLLO SEARCH API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/apollo/search")
async def api_apollo_search(request: Request):
    """Search Apollo for leads matching ICP from neo_eco_config.yaml."""
    body = await request.json()
    page = body.get("page", 1)
    per_page = body.get("per_page", 100)
    location = body.get("location", "")
    keywords = body.get("keywords", "")

    from outbound_engine.apollo_search import search_apollo_leads, export_leads_to_excel

    result = await asyncio.to_thread(search_apollo_leads, page=page, per_page=per_page, location_override=location, keywords_override=keywords)

    if result.get("error"):
        return JSONResponse(status_code=400, content=result)

    # Export to Excel
    leads = result.get("leads", [])
    if leads:
        excel_path = export_leads_to_excel(leads)
        result["excel_path"] = excel_path

    return result


@app.post("/api/apollo/export-to-crm")
async def api_apollo_export_to_crm(request: Request):
    """Import the generated Apollo excel file directly into the CRM database."""
    body = await request.json()
    excel_path = body.get("excel_path", "")
    selected_indices = body.get("selected_indices", None)
    
    if not excel_path:
        return JSONResponse(status_code=400, content={"error": "Missing excel_path"})
    from outbound_engine.lead_manager import import_leads_file
    result = await asyncio.to_thread(import_leads_file, excel_path, selected_indices)
    if "error" in result:
        return JSONResponse(status_code=400, content=result)
    return result


@app.get("/api/apollo/download")
async def api_apollo_download():
    """Download the latest Apollo export as Excel."""
    from outbound_engine.apollo_search import get_latest_export

    filepath = get_latest_export()
    if filepath and Path(filepath).exists():
        return FileResponse(
            filepath,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=Path(filepath).name,
        )
    return JSONResponse(status_code=404, content={"error": "No export file found. Run Apollo search first."})


# ═══════════════════════════════════════════════════════════════
#  SENT MAILS API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/sent-mails")
async def api_sent_mails():
    """Return all sent email logs across all dates, sorted newest first."""
    log_dir = BASE_DIR / "output" / "send_logs"
    all_logs = []
    if log_dir.exists():
        for log_file in sorted(log_dir.glob("*.json"), reverse=True):
            try:
                with open(log_file, "r") as f:
                    day_logs = json.load(f)
                    all_logs.extend(day_logs)
            except Exception:
                pass
    # Sort by timestamp descending (newest first)
    all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {
        "sent_mails": all_logs,
        "total": len(all_logs),
    }


# ═══════════════════════════════════════════════════════════════
#  EMAIL UPLOAD API (User uploads scraped emails)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/leads/upload-emails")
async def api_upload_emails(file: UploadFile = File(...)):
    """
    Accept CSV/Excel upload with email addresses.
    Expected columns: Company Name, Email (minimum).
    Merges emails into existing leads in leads.json.
    """
    from outbound_engine.lead_manager import get_all_leads, _save_leads

    content = await file.read()
    filename = file.filename or "upload.csv"

    leads = get_all_leads()
    company_map = {l["company_name"].lower(): l for l in leads}

    updated_count = 0
    new_count = 0
    errors = []

    try:
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            import pandas as pd
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
            rows = df.to_dict("records")
        else:
            # CSV
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("latin1", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)

        for row in rows:
            company_name = str(row.get("Company Name") or row.get("company_name") or "").strip()
            email = str(row.get("Email") or row.get("email") or "").strip()
            person = str(row.get("Person") or row.get("person") or row.get("Name") or row.get("name") or "").strip()
            title = str(row.get("Primary_Designation") or row.get("Title") or row.get("title") or "").strip()

            if not company_name:
                continue

            if company_name.lower() in company_map:
                lead = company_map[company_name.lower()]
                
                # Update missing company details from re-uploaded file
                lead["about"] = str(row.get("About") or row.get("about") or lead.get("about", "")).strip()
                lead["country"] = str(row.get("Country") or row.get("country") or lead.get("country", "")).strip()
                lead["industry"] = str(row.get("Industry") or row.get("industry") or lead.get("industry", "")).strip()
                lead["employees"] = str(row.get("Employees") or row.get("employees") or lead.get("employees", "")).strip()
                lead["revenue"] = str(row.get("Revenue") or row.get("revenue") or lead.get("revenue", "")).strip()
                lead["founded"] = str(row.get("Founded") or row.get("founded") or lead.get("founded", "")).strip()
                lead["company_phone"] = str(row.get("Company_Phone") or lead.get("company_phone", "")).strip()
                lead["company_linkedin"] = str(row.get("Company_LinkedIn") or lead.get("company_linkedin", "")).strip()

                # Update or add contact with email
                if email:
                    contact_updated = False
                    for contact in lead.get("contacts", []):
                        if not contact.get("email"):
                            contact["email"] = email
                            if person and not contact.get("name"):
                                contact["name"] = person
                            if title and not contact.get("title"):
                                contact["title"] = title
                            contact_updated = True
                            break
                    if not contact_updated:
                        lead.setdefault("contacts", []).append({
                            "name": person,
                            "email": email,
                            "title": title,
                            "phone": "",
                            "linkedin": "",
                            "is_primary": len(lead.get("contacts", [])) == 0,
                        })
                    lead["updated_at"] = datetime.now().isoformat()
                    updated_count += 1
                else:
                    # Still consider it updated if we enriched company details
                    lead["updated_at"] = datetime.now().isoformat()
                    updated_count += 1
            else:
                # New lead from upload
                import uuid
                new_lead = {
                    "id": str(uuid.uuid4())[:8],
                    "company_name": company_name,
                    "website": str(row.get("Website") or row.get("website") or "").strip(),
                    "about": str(row.get("About") or row.get("about") or "").strip(),
                    "country": str(row.get("Country") or row.get("country") or "").strip(),
                    "industry": str(row.get("Industry") or row.get("industry") or "").strip(),
                    "employees": str(row.get("Employees") or row.get("employees") or "").strip(),
                    "revenue": str(row.get("Revenue") or row.get("revenue") or "").strip(),
                    "founded": str(row.get("Founded") or row.get("founded") or "").strip(),
                    "company_phone": str(row.get("Company_Phone") or "").strip(),
                    "company_linkedin": str(row.get("Company_LinkedIn") or "").strip(),
                    "contacts": [],
                    "stage": "new",
                    "score": 0,
                    "tags": [],
                    "notes": [],
                    "campaigns": [],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                if email:
                    new_lead["contacts"].append({
                        "name": person,
                        "email": email,
                        "title": title,
                        "phone": "",
                        "linkedin": "",
                        "is_primary": True,
                    })
                leads.append(new_lead)
                company_map[company_name.lower()] = new_lead
                new_count += 1

        _save_leads(leads)

    except Exception as e:
        return JSONResponse(status_code=400, content={
            "error": f"Failed to process file: {str(e)}",
        })

    return {
        "success": True,
        "updated": updated_count,
        "new": new_count,
        "total_leads": len(leads),
        "message": f"Updated {updated_count} existing leads, added {new_count} new leads",
    }


# ═══════════════════════════════════════════════════════════════
#  EMAIL GENERATION API (Gemini Pro)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/emails/generate")
async def api_generate_email(request: Request):
    body = await request.json()
    lead_id = body.get("lead_id", "")
    email_type = body.get("email_type", "cold_outreach")
    generation_method = body.get("generation_method", "ai")

    from outbound_engine.lead_manager import get_lead
    from outbound_engine.email_generator import generate_email, score_email

    lead = get_lead(lead_id)
    if not lead:
        return JSONResponse(status_code=404, content={"error": "Lead not found"})

    email = await asyncio.to_thread(generate_email, lead, email_type, generation_method=generation_method)
    quality = score_email(email)
    email["quality_score"] = quality

    return email


@app.post("/api/emails/generate-batch")
async def api_generate_batch(request: Request):
    body = await request.json()
    lead_ids = body.get("lead_ids", [])
    email_type = body.get("email_type", "cold_outreach")
    generation_method = body.get("generation_method", "ai")

    from outbound_engine.lead_manager import get_lead
    from outbound_engine.email_generator import generate_email, score_email

    emails = []
    for lid in lead_ids:
        lead = get_lead(lid)
        if lead:
            contact = next((c for c in lead.get("contacts", []) if c.get("email")), None)
            if not contact:
                continue
            email = await asyncio.to_thread(generate_email, lead, email_type, generation_method=generation_method)
            email["lead_id"] = lead.get("id", "")
            email["to_email"] = contact["email"]
            email["to_name"] = contact.get("name", "")
            email["quality_score"] = score_email(email)
            emails.append(email)

    return {"emails": emails, "count": len(emails)}


@app.post("/api/emails/generate-all")
async def api_generate_all_emails(request: Request):
    """Generate personalized emails for selected leads (or all leads with email addresses)."""
    body = await request.json()
    email_type = body.get("email_type", "cold_outreach")
    generation_method = body.get("generation_method", "ai")
    selected_lead_ids = body.get("lead_ids", None)  # Optional: only generate for these

    from outbound_engine.lead_manager import get_all_leads
    from outbound_engine.email_generator import generate_email, score_email

    existing_emails = _load_generated_emails()
    queue_lead_ids = [e.get("lead_id") for e in existing_emails if e.get("lead_id")]

    if selected_lead_ids and len(selected_lead_ids) > 0:
        target_lead_ids = set(selected_lead_ids)
    else:
        target_lead_ids = set(queue_lead_ids)

    all_leads = {l.get("id"): l for l in get_all_leads()}
    existing_map = {e.get("lead_id"): e for e in existing_emails}
    new_count = 0

    if not target_lead_ids:
        return {"error": "No leads in bulk queue. Send leads to Bulk Email first.", "emails": existing_emails, "count": len(existing_emails)}

    for lead_id in target_lead_ids:
        lead = all_leads.get(lead_id)
        if not lead:
            continue

        contact = next((c for c in lead.get("contacts", []) if c.get("email")), None)
        if not contact:
            continue

        email = await asyncio.to_thread(generate_email, lead, email_type, generation_method=generation_method)
        email["lead_id"] = lead_id
        email["to_email"] = contact["email"]
        email["to_name"] = contact.get("name", "")
        email["quality_score"] = score_email(email)
        
        # Merge updated fields with existing (to keep any non-regenerated fields if applicable, or replace them)
        existing_map[lead_id] = email
        new_count += 1

    final_emails = list(existing_map.values())
    _save_generated_emails(final_emails)

    method_label = "AI" if generation_method == "ai" else "template"
    return {
        "emails": final_emails,
        "count": len(final_emails),
        "message": f"Generated {new_count} personalized {method_label} emails",
    }


@app.get("/api/emails/generated")
async def api_get_generated_emails():
    """Get all previously generated emails."""
    emails = _load_generated_emails()
    return {"emails": emails, "count": len(emails)}


@app.post("/api/emails/save-generated")
async def api_save_generated_emails(request: Request):
    """Save generated emails to disk (used when merging from Leads page)."""
    body = await request.json()
    emails = body.get("emails", [])
    _save_generated_emails(emails)
    return {"success": True, "count": len(emails)}


@app.post("/api/emails/send")
async def api_send_campaign(request: Request):
    body = await request.json()
    emails = body.get("emails", [])
    schedule = body.get("schedule", "immediate")

    from outbound_engine.email_sender import send_campaign_emails
    from outbound_engine.lead_manager import update_lead_stage, get_lead
    result = await send_campaign_emails(emails)

    # Auto-update lead stage to "contacted" for successfully sent emails
    for detail in result.get("details", []):
        lead_id = detail.get("lead_id", "")
        if lead_id and detail.get("status") in ("sent", "dry_run"):
            lead = get_lead(lead_id)
            if lead and lead.get("stage") == "new":
                update_lead_stage(lead_id, "contacted", note="Auto-updated: outreach email sent")

    return result


@app.post("/api/emails/send-all")
async def api_send_all_emails(request: Request):
    """Send all previously generated emails."""
    from outbound_engine.email_sender import send_email_async, DRY_RUN, DELAY_SECONDS

    try:
        body = await request.json()
        emails = body.get("emails")
    except Exception:
        emails = None

    if not emails:
        emails = _load_generated_emails()
    if not emails:
        return {"error": "No generated emails to send. Generate emails first.", "results": []}

    results = {"sent": 0, "dry_run": 0, "skipped": 0, "errors": 0, "details": []}

    for i, email_data in enumerate(emails):
        email_data["is_bulk"] = True
        to_email = email_data.get("to_email", "")
        to_name = email_data.get("to_name", email_data.get("contact_name", ""))
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")

        if not to_email:
            results["skipped"] += 1
            results["details"].append({
                "company": email_data.get("company_name", "Unknown"),
                "status": "skipped",
                "reason": "No email address",
            })
            continue

        result = await send_email_async(
            to_email=to_email,
            subject=subject,
            body=body,
            lead_id=email_data.get("lead_id", ""),
            campaign_id=email_data.get("campaign_id", ""),
            is_bulk=True,
        )

        # Auto-update lead stage to "contacted" after successful send
        lid = email_data.get("lead_id", "")
        if lid and result.get("status") in ("sent", "dry_run"):
            from outbound_engine.lead_manager import update_lead_stage, get_lead
            lead = get_lead(lid)
            if lead and lead.get("stage") == "new":
                update_lead_stage(lid, "contacted", note="Auto-updated: outreach email sent")

        status = result.get("status", "error")
        results[status] = results.get(status, 0) + 1
        results["details"].append({
            "company": email_data.get("company_name", "Unknown"),
            "email": to_email,
            **result,
        })

        # Rate limiting — wait between sends to avoid Zoho throttling
        if i < len(emails) - 1 and not DRY_RUN:
            await asyncio.sleep(DELAY_SECONDS)

    results["dry_run_mode"] = DRY_RUN
    results["total_processed"] = len(emails)

    return results


@app.post("/api/emails/send-single")
async def api_send_single_email(request: Request):
    """Send a single generated email immediately."""
    body = await request.json()
    to_email = body.get("to_email", "")
    to_name = body.get("to_name", "")
    subject = body.get("subject", "")
    email_body = body.get("body", "")
    lead_id = body.get("lead_id", "")

    if not to_email or not subject or not email_body:
        return JSONResponse(status_code=400, content={
            "error": "Missing required fields: to_email, subject, body"
        })

    from outbound_engine.email_sender import send_email_async
    from outbound_engine.lead_manager import update_lead_stage, get_lead

    result = await send_email_async(
        to_email=to_email,
        subject=subject,
        body=email_body,
        lead_id=lead_id,
        is_bulk=False,
    )

    # Auto-update lead stage to "contacted" after successful send
    if lead_id and result.get("status") in ("sent", "dry_run"):
        lead = get_lead(lead_id)
        if lead and lead.get("stage") == "new":
            update_lead_stage(lead_id, "contacted", note="Auto-updated: outreach email sent")

    return result


# ═══════════════════════════════════════════════════════════════
#  CAMPAIGN API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/campaigns")
async def api_get_campaigns():
    from outbound_engine.campaign_tracker import get_all_campaigns
    return {"campaigns": get_all_campaigns()}


@app.post("/api/campaigns")
async def api_create_campaign(request: Request):
    body = await request.json()
    from outbound_engine.campaign_tracker import create_campaign
    campaign = create_campaign(
        name=body.get("name", ""),
        email_type=body.get("email_type", "cold_outreach"),
        description=body.get("description", ""),
        target_countries=body.get("target_countries", []),
    )
    return campaign


@app.get("/api/campaigns/{campaign_id}/report")
async def api_campaign_report(campaign_id: str):
    from outbound_engine.campaign_tracker import get_campaign_report
    return get_campaign_report(campaign_id)


@app.get("/api/analytics")
async def api_analytics():
    from outbound_engine.campaign_tracker import get_overall_analytics, get_send_log_summary
    return {
        "campaigns": get_overall_analytics(),
        "send_logs": get_send_log_summary(7),
    }


@app.post("/api/campaigns/sync")
async def api_sync_campaign_stats():
    """Auto-sync all campaign stats from send logs, opens, and replies."""
    from outbound_engine.campaign_tracker import sync_stats_from_logs
    return sync_stats_from_logs()


# ═══════════════════════════════════════════════════════════════
#  OPEN TRACKING
# ═══════════════════════════════════════════════════════════════

# 1x1 transparent GIF
TRACKING_PIXEL = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
    0x01, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF,
    0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x01, 0x00,
    0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3B
])

OPENS_FILE = BASE_DIR / "data" / "email_opens.json"


@app.get("/track/open/{send_id}")
async def track_open(send_id: str, request: Request):
    """Record an email open event and return a 1x1 transparent GIF."""
    try:
        opens = []
        if OPENS_FILE.exists():
            with open(OPENS_FILE, "r") as f:
                opens = json.load(f)

        # Avoid duplicate logging for the same send_id
        existing_ids = {o.get("send_id") for o in opens}
        if send_id not in existing_ids:
            opens.append({
                "send_id": send_id,
                "opened_at": datetime.now().isoformat(),
                "user_agent": request.headers.get("user-agent", ""),
                "ip_address": request.client.host if request.client else "",
            })
            OPENS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OPENS_FILE, "w") as f:
                json.dump(opens, f, indent=2)

            # Automatically sync campaign stats to reflect the new open
            from outbound_engine.campaign_tracker import sync_stats_from_logs
            sync_stats_from_logs()
    except Exception:
        pass  # Never break email rendering

    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@app.get("/api/opens")
async def api_get_opens():
    """Get all email open events."""
    if OPENS_FILE.exists():
        with open(OPENS_FILE, "r") as f:
            opens = json.load(f)
        return {"opens": opens, "total": len(opens)}
    return {"opens": [], "total": 0}


# ═══════════════════════════════════════════════════════════════
#  REPLY TRACKING (IMAP)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/replies/scan")
async def api_scan_replies():
    """Scan inbox for new replies via IMAP."""
    from outbound_engine.reply_tracker import scan_inbox
    result = await asyncio.to_thread(scan_inbox)
    return result


@app.get("/api/replies")
async def api_get_replies():
    """Get all tracked replies."""
    from outbound_engine.reply_tracker import get_all_replies, get_reply_stats
    replies = get_all_replies()
    stats = get_reply_stats()
    return {"replies": replies, "stats": stats}


@app.post("/api/replies/{reply_id}/read")
async def api_mark_reply_read(reply_id: str):
    """Mark a reply as read."""
    from outbound_engine.reply_tracker import mark_reply_read
    success = mark_reply_read(reply_id)
    return {"success": success}


@app.get("/api/replies/stats")
async def api_reply_stats():
    """Get reply statistics."""
    from outbound_engine.reply_tracker import get_reply_stats
    return get_reply_stats()


# ─── Background reply scanner ───
async def _background_reply_scanner():
    """Auto-scan inbox every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        try:
            from outbound_engine.reply_tracker import scan_inbox
            await asyncio.to_thread(scan_inbox)
        except Exception as e:
            print(f"Background scan error: {e}")


# ═══════════════════════════════════════════════════════════════
#  PIPELINE API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/pipeline")
async def api_pipeline_view():
    from sales_pipeline import get_pipeline_view
    return get_pipeline_view()


@app.get("/api/pipeline/analytics")
async def api_pipeline_analytics():
    from sales_pipeline import get_pipeline_analytics
    return get_pipeline_analytics()


@app.get("/api/pipeline/forecast")
async def api_revenue_forecast():
    from sales_pipeline import get_revenue_forecast
    return get_revenue_forecast()


@app.post("/api/pipeline/deals")
async def api_create_deal(request: Request):
    body = await request.json()
    from sales_pipeline import create_deal
    deal = create_deal(
        lead_id=body.get("lead_id", ""),
        company_name=body.get("company_name", ""),
        contact_name=body.get("contact_name", ""),
        estimated_value=body.get("estimated_value", 0),
        product_category=body.get("product_category", ""),
    )
    return deal


@app.post("/api/pipeline/deals/{deal_id}/stage")
async def api_update_deal_stage(deal_id: str, request: Request):
    body = await request.json()
    from sales_pipeline import update_deal_stage
    success = update_deal_stage(deal_id, body.get("stage", ""), body.get("note", ""))
    return {"success": success}


# ═══════════════════════════════════════════════════════════════
#  LEAD SCORING API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/scoring")
async def api_score_all():
    from outbound_engine.lead_manager import get_all_leads
    from sales_pipeline.lead_scorer import score_all_leads, get_score_distribution
    leads = get_all_leads()
    return get_score_distribution(leads)


@app.get("/api/scoring/{lead_id}")
async def api_score_lead(lead_id: str):
    from outbound_engine.lead_manager import get_lead
    from sales_pipeline.lead_scorer import score_lead
    lead = get_lead(lead_id)
    if not lead:
        return JSONResponse(status_code=404, content={"error": "Lead not found"})
    return score_lead(lead)


# ═══════════════════════════════════════════════════════════════
#  BOUNCED LEADS API
# ═══════════════════════════════════════════════════════════════

def _get_bounced_leads() -> list:
    """Scan all send logs for error/bounced entries and return enriched records."""
    send_log_dir = BASE_DIR / "output" / "send_logs"
    bounced = []
    if not send_log_dir.exists():
        return bounced

    for log_file in sorted(send_log_dir.glob("*.json"), reverse=True):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
            for entry in logs:
                if entry.get("status") in ("error", "bounced"):
                    # Try to find the lead for company/contact info
                    lead_id = entry.get("lead_id", "")
                    company_name = ""
                    person = ""
                    country = ""
                    all_emails = entry.get("to_email", "")

                    # Try to get lead info from leads or bin
                    try:
                        from outbound_engine.lead_manager import get_lead, _load_bin
                        lead = get_lead(lead_id)
                        if not lead:
                            bin_leads = _load_bin()
                            lead = next((l for l in bin_leads if l["id"] == lead_id), None)
                        if lead:
                            company_name = lead.get("company_name", "")
                            country = lead.get("country", "")
                            contacts = lead.get("contacts", [])
                            if contacts:
                                person = contacts[0].get("name", "Not found")
                                all_emails = ", ".join(c.get("email", "") for c in contacts if c.get("email"))
                    except Exception:
                        pass

                    bounced.append({
                        "lead_id": lead_id,
                        "company_name": company_name or "-",
                        "person": person or "Not found",
                        "to_email": all_emails,
                        "country": country or "-",
                        "error": entry.get("error", "Unknown error"),
                        "timestamp": entry.get("timestamp", ""),
                        "send_id": entry.get("send_id", ""),
                    })
        except Exception:
            pass

    return bounced


@app.get("/api/bounced")
async def api_get_bounced():
    """Get all bounced/error email entries."""
    bounced = _get_bounced_leads()
    return {"bounced": bounced, "count": len(bounced)}


@app.get("/api/bounced/csv")
async def api_download_bounced_csv():
    """Download bounced leads as CSV in the same format as the upload template."""
    bounced = _get_bounced_leads()
    if not bounced:
        return JSONResponse(status_code=404, content={"error": "No bounced leads to export"})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company Name", "Person", "Email", "Country", "Bounce Reason", "Bounced At"])
    for b in bounced:
        writer.writerow([
            b["company_name"],
            b["person"],
            b["to_email"],
            b["country"],
            b["error"],
            b["timestamp"],
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bounced_leads.csv"},
    )


@app.delete("/api/bounced")
async def api_clear_bounced():
    """Remove all bounced/error entries from send logs."""
    send_log_dir = BASE_DIR / "output" / "send_logs"
    cleared = 0
    if send_log_dir.exists():
        for log_file in send_log_dir.glob("*.json"):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                original_len = len(logs)
                logs = [l for l in logs if l.get("status") not in ("error", "bounced")]
                cleared += original_len - len(logs)
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2, default=str)
            except Exception:
                pass
    return {"success": True, "cleared": cleared, "message": f"Cleared {cleared} bounced entries"}


# ═══════════════════════════════════════════════════════════════
#  BIN / TRASH API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/leads/{lead_id}/delete")
async def api_soft_delete_lead(lead_id: str):
    """Move a lead to the bin (soft delete)."""
    from outbound_engine.lead_manager import move_to_bin
    success = move_to_bin(lead_id)
    if success:
        return {"success": True, "message": "Lead moved to bin"}
    return JSONResponse(status_code=404, content={"error": "Lead not found"})


@app.get("/api/bin")
async def api_get_bin():
    """Get all leads in the bin."""
    from outbound_engine.lead_manager import get_bin_leads
    bin_leads = get_bin_leads()
    return {"leads": bin_leads, "count": len(bin_leads)}


@app.post("/api/bin/{lead_id}/restore")
async def api_restore_lead(lead_id: str):
    """Restore a lead from the bin back to active leads."""
    from outbound_engine.lead_manager import restore_from_bin
    success = restore_from_bin(lead_id)
    if success:
        return {"success": True, "message": "Lead restored"}
    return JSONResponse(status_code=404, content={"error": "Lead not found in bin"})


@app.delete("/api/bin/{lead_id}")
async def api_permanent_delete(lead_id: str):
    """Permanently delete a lead from the bin."""
    from outbound_engine.lead_manager import permanent_delete
    success = permanent_delete(lead_id)
    if success:
        return {"success": True, "message": "Lead permanently deleted"}
    return JSONResponse(status_code=404, content={"error": "Lead not found in bin"})


@app.delete("/api/bin")
async def api_empty_bin():
    """Empty the entire bin — permanently delete all."""
    from outbound_engine.lead_manager import empty_bin
    count = empty_bin()
    return {"success": True, "deleted": count, "message": f"Permanently deleted {count} leads"}


# ═══════════════════════════════════════════════════════════════
#  CONTENT OPS API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/content/catalog")
async def api_catalog():
    from content_ops.catalog_generator import generate_catalog_markdown
    return {"content": generate_catalog_markdown(), "format": "markdown"}


@app.post("/api/content/catalog/save")
async def api_save_catalog(request: Request):
    body = await request.json()
    from content_ops.catalog_generator import save_catalog
    filepath = save_catalog(format=body.get("format", "markdown"))
    return {"filepath": filepath}


@app.get("/api/content/case-studies")
async def api_case_studies():
    from content_ops.case_study_generator import list_case_studies
    return {"case_studies": list_case_studies()}


@app.post("/api/content/case-studies")
async def api_create_case_study(request: Request):
    body = await request.json()
    from content_ops.case_study_generator import create_case_study, generate_case_study_markdown
    cs = create_case_study(
        client_name=body.get("client_name", ""),
        industry=body.get("industry", ""),
        country=body.get("country", ""),
        challenge=body.get("challenge", ""),
        solution=body.get("solution", ""),
        results=body.get("results", {}),
        testimonial=body.get("testimonial", ""),
        title=body.get("title", ""),
    )
    cs["markdown"] = generate_case_study_markdown(cs)
    return cs


@app.get("/api/content/calendar")
async def api_content_calendar(month: Optional[str] = None, quarter: Optional[int] = None):
    from content_ops.content_calendar import generate_monthly_calendar, generate_quarterly_calendar
    if quarter:
        return generate_quarterly_calendar(quarter)
    return generate_monthly_calendar(month)


@app.post("/api/content/score")
async def api_score_content(request: Request):
    body = await request.json()
    from content_ops.quality_scorer import score_content
    return score_content(
        content=body.get("content", ""),
        content_type=body.get("content_type", "email"),
    )


# ═══════════════════════════════════════════════════════════════
#  DEAL RESURRECTOR API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/resurrector")
async def api_cold_deals():
    from sales_pipeline.deal_resurrector import get_resurrection_report
    return get_resurrection_report()


# ═══════════════════════════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    import os
    return {
        "status": "healthy",
        "service": "Neo Eco Cleaning AI Marketing Dashboard",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "llm": "Gemini Pro" if os.environ.get("GEMINI_API_KEY") else "Template (no API key)",
        "apollo": "Connected" if os.environ.get("APOLLO_API_KEY") else "Not configured",
        "dry_run": os.environ.get("DRY_RUN", "true"),
    }


# ─── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import os
    host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.environ.get("DASHBOARD_PORT", "8000"))
    print(f"\n🚀 Neo Eco Cleaning AI Marketing Dashboard v2.0")
    print(f"   http://{host}:{port}")
    print(f"   API docs: http://{host}:{port}/docs\n")
    uvicorn.run(app, host=host, port=port)
