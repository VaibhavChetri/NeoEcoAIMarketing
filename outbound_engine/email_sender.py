"""
Neo Eco Cleaning — Email Sender
==================================
SMTP email sending with tracking pixels, rate limiting,
GDPR-compliant unsubscribe, and send logging.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from tz_utils import now_ist
from typing import List, Dict, Optional
import asyncio

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SMTP Config
SMTP_HOST = os.environ.get("SMTP_HOST", "smtppro.zoho.in")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "hello@neoecocleaning.co.uk")
SENDER_NAME = os.environ.get("SENDER_NAME", "Neo Eco Cleaning")

MAX_PER_DAY = int(os.environ.get("MAX_EMAILS_PER_DAY", "30"))
DELAY_SECONDS = int(os.environ.get("EMAIL_DELAY_SECONDS", "60"))
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() == "true"

SEND_LOG_DIR = BASE_DIR / "output" / "send_logs"
TRACKING_BASE_URL = os.environ.get("TRACKING_BASE_URL", "https://neoecoaimarketing.onrender.com")


def _get_daily_send_count() -> int:
    today = now_ist().strftime("%Y-%m-%d")
    log_file = SEND_LOG_DIR / f"{today}.json"
    if log_file.exists():
        with open(log_file, "r") as f:
            logs = json.load(f)
            return sum(1 for l in logs if l.get("status") == "sent")
    return 0


def _log_send(entry: Dict):
    SEND_LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = now_ist().strftime("%Y-%m-%d")
    log_file = SEND_LOG_DIR / f"{today}.json"

    logs = []
    if log_file.exists():
        with open(log_file, "r") as f:
            logs = json.load(f)

    logs.append(entry)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2, default=str)


def _build_html_email(
    body: str,
    subject: str = "",
    send_id: str = "",
    include_tracking: bool = True,
    include_unsubscribe: bool = True,
    to_email: str = "",
) -> str:
    """Build professional HTML email with Neo Eco Cleaning branding."""

    # Convert plain text to HTML paragraphs
    paragraphs = body.split("\n\n")
    html_paras = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Handle bullet points
        if p.startswith("•") or p.startswith("-") or p.startswith("*"):
            lines = p.split("\n")
            items = "".join(
                f'<li style="margin-bottom:6px;color:#374151;font-size:14px;line-height:1.6;">'
                f'{line.lstrip("•-* ").strip()}</li>'
                for line in lines if line.strip()
            )
            html_paras.append(f'<ul style="padding-left:20px;margin:12px 0;">{items}</ul>')
        else:
            html_paras.append(
                f'<p style="margin:0 0 16px 0;color:#374151;font-size:14px;line-height:1.7;">'
                f'{p.replace(chr(10), "<br/>")}</p>'
            )

    body_html = "".join(html_paras)

    # Tracking pixel
    tracking_pixel = ""
    if include_tracking and send_id:
        tracking_pixel = (
            f'<img src="{TRACKING_BASE_URL}/track/open/{send_id}" '
            f'width="1" height="1" style="display:none;" alt="" />'
        )

    # Unsubscribe
    unsub = ""
    if include_unsubscribe:
        unsub_url = f"{TRACKING_BASE_URL}/unsubscribe?email={to_email}" if to_email else "#"
        unsub = (
            f'<p style="margin-top:20px;font-size:11px;color:#9ca3af;text-align:center;">'
            f'You received this email because your company was identified as a potential fit for '
            f'our eco-friendly cleaning services. '
            f'<a href="{unsub_url}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>'
            f'</p>'
        )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
  <!-- Header Bar -->
  <tr><td style="background:linear-gradient(135deg,#059669,#10b981);padding:3px 0;"></td></tr>
  <!-- Body -->
  <tr><td style="padding:32px 36px 24px 36px;">
    {body_html}
  </td></tr>
  <!-- Signature -->
  <tr><td style="padding:0 36px 24px 36px;border-top:1px solid #e5e7eb;">
    <img src="https://files.catbox.moe/3ycvuj.jpeg" alt="Neo Eco Cleaning Logo" style="max-height: 80px; display: block; margin: 16px 0;" />
    <p style="margin:0 0 4px 0;font-size:13px;color:#374151;font-weight:600;">Neo Eco Cleaning Team</p>
    <p style="margin:0;font-size:12px;color:#6b7280;line-height:1.5;">
      Professional Eco-Friendly Cleaning · North London<br/>
      📞 077680 66860 (whatsapp)<br/>
      📞 07438885267 (phone)<br/>
      📧 hello@neoecocleaning.co.uk<br/>
      🌐 <a href="https://neoecocleaning.co.uk" style="color:#059669;text-decoration:none;">neoecocleaning.co.uk</a>
    </p>
  </td></tr>
  <!-- Footer -->
  <tr><td style="background:#f3f4f6;padding:16px 36px;">
    {unsub}
  </td></tr>
</table>
{tracking_pixel}
</td></tr></table>
</body>
</html>"""


async def send_email_async(
    to_email: str,
    subject: str,
    body: str,
    lead_id: str = "",
    campaign_id: str = "",
    is_bulk: bool = False,
    dry_run: Optional[bool] = None,
) -> Dict:
    """Send a single email via SMTP (async)."""
    if dry_run is None:
        dry_run = DRY_RUN

    # Sanitize email address — strip whitespace and trailing commas
    to_email = to_email.strip().rstrip(",").strip()

    send_id = str(uuid.uuid4())[:12]

    # Resolve company and to_name for logging
    company = ""
    to_name = ""
    if lead_id:
        from outbound_engine.lead_manager import get_lead
        lead = get_lead(lead_id)
        if lead:
            company = lead.get("company_name", "")
            for c in lead.get("contacts", []):
                if c.get("email", "").strip().lower() == to_email.lower():
                    to_name = c.get("name", "")
                    break

    # Check daily limit
    if _get_daily_send_count() >= MAX_PER_DAY and not dry_run:
        result = {
            "status": "skipped",
            "reason": f"Daily limit reached ({MAX_PER_DAY})",
            "to_email": to_email,
            "to_name": to_name,
            "company": company,
            "send_id": send_id,
            "timestamp": now_ist().isoformat(),
        }
        _log_send(result)
        return result

    # Check opt-out
    from outbound_engine.lead_manager import is_opted_out
    if is_opted_out(to_email):
        result = {
            "status": "skipped",
            "reason": "Opted out",
            "to_email": to_email,
            "to_name": to_name,
            "company": company,
            "send_id": send_id,
            "timestamp": now_ist().isoformat(),
        }
        _log_send(result)
        return result

    html_body = _build_html_email(body, subject, send_id, to_email=to_email)

    if dry_run:
        result = {
            "status": "dry_run",
            "to_email": to_email,
            "to_name": to_name,
            "company": company,
            "subject": subject,
            "body": body,
            "send_id": send_id,
            "lead_id": lead_id,
            "campaign_id": campaign_id,
            "is_bulk": is_bulk,
            "timestamp": now_ist().isoformat(),
        }
        _log_send(result)
        return result

    api_provider = os.environ.get("EMAIL_API_PROVIDER", "").lower()
    api_key = os.environ.get("EMAIL_API_KEY", "")

    max_retries = 3
    retry_delay = DELAY_SECONDS * 2  
    resend_email_id = ""

    for attempt in range(max_retries + 1):
        try:
            if api_provider == "resend" and api_key:
                import httpx

                payload = {
                    "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "text": body,
                    "headers": {
                        "X-Send-ID": send_id
                    },
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if response.status_code >= 400:
                        raise Exception(f"Resend API Error {response.status_code}: {response.text}")
                    else:
                        resp_data = response.json()
                        resend_email_id = resp_data.get("id", "")
            else:
                # Original SMTP Fallback
                import aiosmtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.mime.image import MIMEImage

                msg_root = MIMEMultipart("related")
                msg_root["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
                msg_root["To"] = to_email
                msg_root["Subject"] = subject
                msg_root["X-Send-ID"] = send_id

                msg_alt = MIMEMultipart("alternative")
                msg_root.attach(msg_alt)

                msg_alt.attach(MIMEText(body, "plain", "utf-8"))
                msg_alt.attach(MIMEText(html_body, "html", "utf-8"))

                await aiosmtplib.send(
                    msg_root,
                    hostname=SMTP_HOST,
                    port=SMTP_PORT,
                    username=SMTP_USERNAME,
                    password=SMTP_PASSWORD,
                    use_tls=(SMTP_PORT == 465),
                    start_tls=(SMTP_PORT != 465),
                )

            # Success
            result = {
                "status": "sent",
                "to_email": to_email,
                "to_name": to_name,
                "company": company,
                "subject": subject,
                "body": body,
                "send_id": send_id,
                "resend_email_id": resend_email_id,
                "lead_id": lead_id,
                "campaign_id": campaign_id,
                "is_bulk": is_bulk,
                "timestamp": now_ist().isoformat(),
            }
            if attempt > 0:
                result["retries"] = attempt
            _log_send(result)
            return result

        except Exception as e:
            error_str = str(e)
            is_rate_limit = "429" in error_str or "Too Many Requests" in error_str or "5.4.6" in error_str

            if is_rate_limit and attempt < max_retries:
                wait_time = retry_delay * (2 ** attempt)
                print(f"    ⏳ Rate limit hit for {to_email}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue

            result = {
                "status": "error",
                "to_email": to_email,
                "to_name": to_name,
                "company": company,
                "subject": subject,
                "body": body,
                "error": error_str,
                "send_id": send_id,
                "lead_id": lead_id,
                "campaign_id": campaign_id,
                "timestamp": now_ist().isoformat(),
            }
            if attempt > 0:
                result["retries"] = attempt
            _log_send(result)
            return result


def send_email_sync(
    to_email: str,
    subject: str,
    body: str,
    lead_id: str = "",
    campaign_id: str = "",
) -> Dict:
    """Synchronous wrapper for send_email_async."""
    return asyncio.run(
        send_email_async(to_email, subject, body, lead_id, campaign_id)
    )


async def send_campaign_emails(
    emails: List[Dict],
    delay_seconds: Optional[int] = None,
    dry_run: Optional[bool] = None,
) -> Dict:
    """Send a batch of campaign emails with rate limiting."""
    if delay_seconds is None:
        delay_seconds = DELAY_SECONDS
    if dry_run is None:
        dry_run = DRY_RUN

    results = {"sent": 0, "skipped": 0, "errors": 0, "dry_run": 0, "details": []}

    for i, email in enumerate(emails):
        to_email = email.get("to_email", "")
        if not to_email:
            # Try to get from lead contacts
            lead = email.get("lead", {})
            contacts = lead.get("contacts", [])
            to_email = contacts[0].get("email", "") if contacts else ""

        if not to_email:
            results["skipped"] += 1
            continue

        result = await send_email_async(
            to_email=to_email,
            subject=email.get("subject", ""),
            body=email.get("body", ""),
            lead_id=email.get("lead_id", ""),
            campaign_id=email.get("campaign_id", ""),
            is_bulk=True,
            dry_run=dry_run,
        )

        results[result["status"]] = results.get(result["status"], 0) + 1
        results["details"].append(result)

        # Rate limiting
        if i < len(emails) - 1 and not dry_run:
            await asyncio.sleep(delay_seconds)

    return results


def get_today_send_count() -> int:
    return _get_daily_send_count()


def get_send_history(days: int = 7) -> List[Dict]:
    """Get send history for the last N days."""
    from datetime import timedelta
    history = []
    for i in range(days):
        day = (now_ist() - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = SEND_LOG_DIR / f"{day}.json"
        if log_file.exists():
            with open(log_file, "r") as f:
                logs = json.load(f)
                history.extend(logs)
    return history
