"""
Neo Eco Cleaning — Reply Tracker
==================================
IMAP-based reply tracking for the CRM.
Connects to the mailbox, scans for incoming replies,
matches them against leads, and auto-updates lead stages.
"""

import imaplib
import email
import json
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from tz_utils import now_ist
from typing import List, Dict, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
REPLIES_FILE = DATA_DIR / "replies.json"
SEND_LOG_DIR = BASE_DIR / "output" / "send_logs"

# IMAP Configuration
IMAP_HOST = os.environ.get("IMAP_HOST", "imappro.zoho.in")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USERNAME = os.environ.get("IMAP_USERNAME", os.environ.get("SMTP_USERNAME", ""))
IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", os.environ.get("SMTP_PASSWORD", ""))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")

# How many days back to scan
SCAN_DAYS = int(os.environ.get("REPLY_SCAN_DAYS", "3"))


def _load_replies() -> List[Dict]:
    if REPLIES_FILE.exists():
        with open(REPLIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_replies(replies: List[Dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPLIES_FILE, "w", encoding="utf-8") as f:
        json.dump(replies, f, indent=2, ensure_ascii=False, default=str)


def _decode_header_value(value):
    """Decode email header (handles encoded words)."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _extract_body(msg) -> str:
    """Extract plain-text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disp = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disp:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    pass
        # Fallback to HTML if no plain text
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        html = part.get_payload(decode=True).decode(charset, errors="replace")
                        body = re.sub(r"<[^>]+>", " ", html)
                        body = re.sub(r"\s+", " ", body).strip()
                        break
                    except Exception:
                        pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body.strip()


def _strip_quoted_reply(text: str) -> str:
    """Strip quoted original email from a reply."""
    if not text:
        return ""

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    reply_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            break
        if re.match(r"^On .+ wrote:$", stripped):
            break
        if stripped.startswith("On ") and "wrote:" in stripped:
            break
        if stripped.startswith("From:") and ("Sent:" in text or "To:" in text):
            break
        if stripped == "------- Original Message -------":
            break
        if re.match(r"^[_\-=]{10,}$", stripped):
            break
        reply_lines.append(line)

    result = "\n".join(reply_lines).strip()
    result = re.split(
        r"\s*On \d{1,2} \w{3} \d{4},? at \d{1,2}:\d{2}.+?wrote:",
        result, maxsplit=1,
    )[0].strip()
    result = result.replace("&nbsp;", " ").replace("&amp;", "&")
    result = re.sub(r"&lt;.*?&gt;", "", result)
    result = re.sub(r"\s{2,}", " ", result).strip()
    return result


def _get_sent_recipients() -> set:
    """Build a set of email addresses we've actually sent to from the CRM.
    Only considers successfully sent emails (status='sent')."""
    sent_emails = set()
    if not SEND_LOG_DIR.exists():
        return sent_emails

    for log_file in SEND_LOG_DIR.glob("*.json"):
        try:
            with open(log_file, "r") as f:
                logs = json.load(f)
                for entry in logs:
                    if entry.get("status") == "sent":
                        to_email = entry.get("to_email", "").lower().strip()
                        if to_email:
                            sent_emails.add(to_email)
        except (json.JSONDecodeError, IOError):
            continue

    return sent_emails


def _update_send_log_to_bounced(bounced_email: str, error_reason: str):
    """Update a send log entry from 'sent' to 'bounced' when we detect a bounce notification."""
    if not SEND_LOG_DIR.exists():
        return False

    bounced_email = bounced_email.lower().strip()
    updated = False

    for log_file in SEND_LOG_DIR.glob("*.json"):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)

            for entry in logs:
                if (entry.get("status") == "sent" and
                    entry.get("to_email", "").lower().strip() == bounced_email):
                    entry["status"] = "bounced"
                    entry["error"] = error_reason
                    entry["bounced_at"] = now_ist().isoformat()
                    updated = True

            if updated:
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False, default=str)
                return True
        except Exception:
            continue

    return updated


def _extract_bounced_email(body: str) -> Optional[str]:
    """Extract the bounced recipient email address from a bounce notification body."""
    if not body:
        return None

    # Pattern 1: "Final-Recipient: rfc822; user@domain.com"
    match = re.search(r'Final-Recipient:\s*rfc822;\s*(\S+@\S+)', body)
    if match:
        return match.group(1).strip().rstrip(',').rstrip('>')

    # Pattern 2: "user@domain.com, ERROR CODE" (Zoho format)
    match = re.search(r'(\S+@\S+),\s*ERROR CODE', body)
    if match:
        return match.group(1).strip()

    # Pattern 3: "Original-Recipient: rfc822; user@domain.com"
    match = re.search(r'Original-Recipient:\s*rfc822;\s*(\S+@\S+)', body)
    if match:
        return match.group(1).strip().rstrip(',').rstrip('>')

    # Pattern 4: "could not be delivered to" or "delivery to" followed by email
    match = re.search(r'(?:delivered to|delivery to|deliver to)\s+<?(\S+@\S+?)>?[\s,.]', body, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Pattern 5: Generic email pattern after "550" or "5.4" error codes
    match = re.search(r'<(\S+@\S+?)>\s*.*?(?:550|5\.\d\.\d)', body)
    if match:
        return match.group(1).strip()

    return None


def scan_inbox(days: int = None) -> Dict:
    """Connect to IMAP, scan inbox for replies and bounce notifications."""
    if days is None:
        days = SCAN_DAYS

    if not IMAP_USERNAME or not IMAP_PASSWORD:
        return {
            "error": "IMAP credentials not configured. Add IMAP_USERNAME and IMAP_PASSWORD to .env",
            "new_replies": 0,
            "replies": [],
        }

    # We previously only checked `sent_recipients` from local log files.
    # Because Render wipes local files, we'll now accept replies from anyone 
    # who is listed as a contact in the CRM.
    existing_replies = _load_replies()
    existing_msg_ids = {r.get("message_id") for r in existing_replies if r.get("message_id")}

    from outbound_engine.lead_manager import get_all_leads, update_lead_stage
    all_leads = get_all_leads()

    email_to_lead = {}
    for lead in all_leads:
        for contact in lead.get("contacts", []):
            email_addr = contact.get("email", "").lower().strip()
            # If the sender is in our CRM as a contact, we should track their replies.
            if email_addr:
                email_to_lead[email_addr] = {
                    "lead_id": lead["id"],
                    "company_name": lead["company_name"],
                    "contact_name": contact.get("name", ""),
                    "contact_email": email_addr,
                }

    new_replies = []
    new_bounces = []
    errors = []
    # Track already-processed bounce message IDs to avoid duplicates
    BOUNCES_FILE = DATA_DIR / "detected_bounces.json"
    processed_bounce_ids = set()
    if BOUNCES_FILE.exists():
        try:
            with open(BOUNCES_FILE, "r") as f:
                processed_bounce_ids = set(json.load(f))
        except Exception:
            pass

    try:
        print(f"📬 Connecting to {IMAP_HOST}:{IMAP_PORT}...")
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)
        mail.select("INBOX")

        since_date = (now_ist() - timedelta(days=days)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{since_date}")')

        if status != "OK":
            mail.logout()
            return {"error": "Failed to search inbox", "new_replies": 0, "replies": []}

        msg_ids = messages[0].split()
        print(f"📧 Found {len(msg_ids)} emails in the last {days} days")
        print(f"🎯 Filtering for replies from {len(email_to_lead)} CRM contact(s)")

        scanned = 0
        for msg_id in msg_ids:
            try:
                status, header_data = mail.fetch(msg_id, "(BODY[HEADER.FIELDS (FROM MESSAGE-ID SUBJECT DATE IN-REPLY-TO REFERENCES)])")
                if status != "OK":
                    continue

                header_bytes = header_data[0][1]
                header_msg = email.message_from_bytes(header_bytes)

                message_id = header_msg.get("Message-ID", "")
                if message_id in existing_msg_ids:
                    continue

                from_header = _decode_header_value(header_msg.get("From", ""))
                from_name, from_email_addr = parseaddr(from_header)
                from_email_addr = from_email_addr.lower().strip()
                subject = _decode_header_value(header_msg.get("Subject", ""))

                # ─── BOUNCE DETECTION ───
                is_bounce = (
                    "mailer-daemon" in from_email_addr or
                    "postmaster" in from_email_addr or
                    "undelivered" in subject.lower() or
                    "delivery status" in subject.lower() or
                    "mail delivery failed" in subject.lower() or
                    "returned to sender" in subject.lower() or
                    "undeliverable" in subject.lower()
                )

                if is_bounce and message_id not in processed_bounce_ids:
                    # Fetch full body to extract bounced email address
                    try:
                        status2, body_data = mail.fetch(msg_id, "(RFC822)")
                        if status2 == "OK" and body_data[0][1]:
                            full_msg = email.message_from_bytes(body_data[0][1])
                            body = _extract_body(full_msg)
                            bounced_email = _extract_bounced_email(body)

                            if bounced_email and bounced_email.lower() in email_to_lead:
                                # Extract error reason
                                error_reason = "Bounced — delivery failed"
                                error_match = re.search(r'(ERROR CODE[^\n]+|Diagnostic-Code:[^\n]+|Status:\s*\d[^\n]+)', body)
                                if error_match:
                                    error_reason = error_match.group(1).strip()

                                # Update send log from "sent" to "bounced"
                                was_updated = _update_send_log_to_bounced(bounced_email, error_reason)
                                if was_updated:
                                    new_bounces.append(bounced_email)
                                    print(f"  📛 BOUNCE detected: {bounced_email} — {error_reason[:60]}")

                                processed_bounce_ids.add(message_id)
                    except Exception as e:
                        errors.append(f"Error processing bounce: {str(e)}")
                    continue

                # ─── REPLY DETECTION (existing logic) ───
                if from_email_addr == SENDER_EMAIL.lower():
                    continue

                if from_email_addr not in email_to_lead:
                    continue

                lead_info = email_to_lead[from_email_addr]
                in_reply_to = header_msg.get("In-Reply-To", "")
                references = header_msg.get("References", "")
                
                # Verify that it's a genuine reply to an existing thread
                is_reply = bool(in_reply_to or references or str(subject).strip().lower().startswith("re:"))
                if not is_reply:
                    continue

                date_str = header_msg.get("Date", "")

                body = ""
                try:
                    status2, body_data = mail.fetch(msg_id, "(RFC822)")
                    if status2 == "OK" and body_data[0][1]:
                        full_msg = email.message_from_bytes(body_data[0][1])
                        body = _extract_body(full_msg)
                except Exception as e:
                    print(f"Failed to parse body: {e}")

                try:
                    received_at = parsedate_to_datetime(date_str).isoformat()
                except Exception:
                    received_at = now_ist().isoformat()

                reply_record = {
                    "id": f"reply_{now_ist().strftime('%Y%m%d%H%M%S')}_{scanned}",
                    "message_id": message_id,
                    "from_email": from_email_addr,
                    "from_name": from_name or lead_info["contact_name"],
                    "lead_id": lead_info["lead_id"],
                    "company_name": lead_info["company_name"],
                    "subject": subject,
                    "body_preview": _strip_quoted_reply(body)[:500] if body else "",
                    "received_at": received_at,
                    "scanned_at": now_ist().isoformat(),
                    "read": False,
                    "sentiment": _quick_sentiment(body),
                }

                new_replies.append(reply_record)

                try:
                    update_lead_stage(
                        lead_info["lead_id"],
                        "replied",
                        f"Auto-detected reply from {from_email_addr}: {subject}"
                    )
                except Exception as e:
                    errors.append(f"Failed to update lead {lead_info['lead_id']}: {str(e)}")

                scanned += 1
                print(f"  ✅ Reply from {lead_info['company_name']} ({from_email_addr}): {subject[:60]}")

            except Exception as e:
                errors.append(f"Error processing message: {str(e)}")
                continue

        mail.logout()

    except imaplib.IMAP4.error as e:
        return {
            "error": f"IMAP authentication failed: {str(e)}. Check IMAP credentials in .env",
            "new_replies": 0,
            "replies": [],
        }
    except Exception as e:
        return {
            "error": f"IMAP connection failed: {str(e)}",
            "new_replies": 0,
            "replies": [],
        }

    if new_replies:
        all_replies = new_replies + existing_replies
        _save_replies(all_replies)

    # Save processed bounce IDs to avoid re-processing
    if new_bounces:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(BOUNCES_FILE, "w") as f:
                json.dump(list(processed_bounce_ids), f, indent=2)
        except Exception:
            pass

        # Sync campaign stats to reflect new bounces
        try:
            from outbound_engine.campaign_tracker import sync_stats_from_logs
            sync_stats_from_logs()
        except Exception:
            pass

    return {
        "new_replies": len(new_replies),
        "total_replies": len(existing_replies) + len(new_replies),
        "replies": new_replies,
        "new_bounces": len(new_bounces),
        "bounced_emails": new_bounces,
        "scanned_emails": len(msg_ids) if 'msg_ids' in dir() else 0,
        "errors": errors if errors else None,
    }


def _quick_sentiment(text: str) -> str:
    """Quick keyword-based sentiment detection for replies."""
    if not text:
        return "neutral"

    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith(">"):
            break
        if line.startswith("On ") and "wrote:" in line:
            break
        if line.startswith("From:") and ("Sent:" in text or "To:" in text):
            break
        if "________________________________" in line:
            break
        cleaned_lines.append(line)

    cleaned_text = " ".join(cleaned_lines)
    text_lower = cleaned_text.lower()

    positive = ["interested", "great", "love", "wonderful", "perfect",
                 "yes", "absolutely", "let's", "schedule", "meeting",
                 "call", "discuss", "quote", "survey", "site visit",
                 "look forward", "excited", "happy to", "keen",
                 "cleaning", "properties"]
    negative = ["not interested", "unsubscribe", "remove", "stop",
                "no thanks", "no thank you", "don't contact", "spam",
                "not relevant", "opt out"]

    for word in negative:
        if word in text_lower:
            return "negative"
    for word in positive:
        if word in text_lower:
            return "positive"
    return "neutral"


def get_all_replies() -> List[Dict]:
    return _load_replies()


def get_replies_for_lead(lead_id: str) -> List[Dict]:
    return [r for r in _load_replies() if r.get("lead_id") == lead_id]


def get_unread_count() -> int:
    return sum(1 for r in _load_replies() if not r.get("read", False))


def mark_reply_read(reply_id: str) -> bool:
    replies = _load_replies()
    for reply in replies:
        if reply["id"] == reply_id:
            reply["read"] = True
            _save_replies(replies)
            return True
    return False


def mark_all_read() -> int:
    replies = _load_replies()
    count = 0
    for reply in replies:
        if not reply.get("read", False):
            reply["read"] = True
            count += 1
    if count > 0:
        _save_replies(replies)
    return count


def get_reply_stats() -> Dict:
    replies = _load_replies()
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}
    companies = {}

    for r in replies:
        sentiments[r.get("sentiment", "neutral")] += 1
        company = r.get("company_name", "Unknown")
        companies[company] = companies.get(company, 0) + 1

    return {
        "total_replies": len(replies),
        "unread": sum(1 for r in replies if not r.get("read", False)),
        "sentiments": sentiments,
        "by_company": dict(sorted(companies.items(), key=lambda x: -x[1])),
        "latest": replies[0] if replies else None,
    }
