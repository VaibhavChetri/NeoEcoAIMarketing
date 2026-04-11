"""
Neo Eco Cleaning — Lead Manager
=================================
Import, search, filter, and manage leads for North London cleaning outreach.
"""

import json
import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LEADS_FILE = DATA_DIR / "leads.json"
OPTOUTS_FILE = DATA_DIR / "optouts.json"
BIN_FILE = DATA_DIR / "bin.json"

LEAD_STAGES = [
    "new", "contacted", "replied", "meeting_booked",
    "negotiation", "won", "lost", "opted_out",
]


def _load_leads() -> List[Dict]:
    if LEADS_FILE.exists():
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_leads(leads: List[Dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False, default=str)


def _load_optouts() -> List[str]:
    if OPTOUTS_FILE.exists():
        with open(OPTOUTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_optouts(optouts: List[str]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OPTOUTS_FILE, "w", encoding="utf-8") as f:
        json.dump(optouts, f, indent=2)


def import_leads_file(file_path: str, selected_indices: Optional[List[int]] = None) -> Dict:
    """Import leads from CSV or Excel file."""
    file_path = Path(file_path)
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    existing_leads = _load_leads()
    existing_companies = {l["company_name"].lower() for l in existing_leads if l.get("company_name")}
    new_leads = []

    try:
        import pandas as pd
        if file_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path, engine="openpyxl")
        else:
            df = pd.read_csv(file_path)
        df.fillna("", inplace=True)
        rows = df.to_dict("records")
    except Exception as e:
        return {"error": f"Failed to parse file: {str(e)}"}

    for i, row in enumerate(rows):
        if selected_indices is not None and i not in selected_indices:
            continue
        
        company_name = str(row.get("Company Name", "")).strip()
        if not company_name or company_name.lower() in existing_companies:
            continue

        lead = {
            "id": str(uuid.uuid4())[:8],
            "company_name": company_name,
            "website": str(row.get("Website", "")).strip(),
            "about": (str(row.get("Company Description", "")).strip() or str(row.get("About", "")).strip()),
            "country": str(row.get("Country", row.get("Area", ""))).strip(),
            "industry": str(row.get("Industry", "")).strip(),
            "employees": str(row.get("Employees", "")).strip(),
            "revenue": str(row.get("Revenue", "")).strip(),
            "founded": str(row.get("Founded", "")).strip(),
            "company_phone": str(row.get("Company_Phone", row.get("Phone", ""))).strip(),
            "company_linkedin": str(row.get("Company_LinkedIn", "")).strip(),
            "contacts": [],
            "stage": "new",
            "score": 0,
            "tags": [],
            "notes": [],
            "campaigns": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Primary contact
        person = str(row.get("Person", row.get("Contact Name", ""))).strip()
        email = str(row.get("Email", "")).strip()
        designation = str(row.get("Primary_Designation", row.get("Title", ""))).strip()
        if person or email:
            lead["contacts"].append({
                "name": person, "email": email, "title": designation,
                "phone": str(row.get("Primary_Phone", row.get("Contact Phone", ""))).strip(),
                "linkedin": str(row.get("Primary_LinkedIn", "")).strip(),
                "is_primary": True,
            })

        # Alternate contacts
        for prefix, name_key, email_key, title_key in [
            ("alt1", "Alternate_Person_Name", "Alternate_Email", "Alternate_Designation"),
            ("alt2", "Alternate2_Name", "Alternate2_Email", "Alternate2_Title"),
        ]:
            alt_name = str(row.get(name_key, "")).strip()
            alt_email = str(row.get(email_key, "")).strip()
            alt_title = str(row.get(title_key, "")).strip()
            if alt_name or alt_email:
                lead["contacts"].append({
                    "name": alt_name, "email": alt_email, "title": alt_title,
                    "phone": "", "linkedin": "", "is_primary": False,
                })

        new_leads.append(lead)
        existing_companies.add(company_name.lower())

    all_leads = existing_leads + new_leads
    _save_leads(all_leads)

    return {
        "total_imported": len(new_leads),
        "total_in_database": len(all_leads),
        "skipped_duplicates": len(existing_leads),
    }


def get_all_leads() -> List[Dict]:
    return _load_leads()


def get_lead(lead_id: str) -> Optional[Dict]:
    for lead in _load_leads():
        if lead["id"] == lead_id:
            return lead
    return None


def search_leads(
    country: Optional[str] = None,
    industry: Optional[str] = None,
    stage: Optional[str] = None,
    min_employees: Optional[int] = None,
    max_employees: Optional[int] = None,
    has_email: Optional[bool] = None,
    query: Optional[str] = None,
) -> List[Dict]:
    """Search and filter leads."""
    leads = _load_leads()
    results = []

    for lead in leads:
        if country and country.lower() not in lead.get("country", "").lower():
            continue
        if industry and industry.lower() not in lead.get("industry", "").lower():
            continue
        if stage and lead.get("stage") != stage:
            continue

        try:
            emp = int(str(lead.get("employees", "0")).replace(",", ""))
        except (ValueError, TypeError):
            emp = 0
        if min_employees and emp < min_employees:
            continue
        if max_employees and emp > max_employees:
            continue

        if has_email is not None:
            has = any(c.get("email") for c in lead.get("contacts", []))
            if has_email != has:
                continue

        if query:
            searchable = f"{lead.get('company_name', '')} {lead.get('about', '')} {lead.get('industry', '')}".lower()
            if query.lower() not in searchable:
                continue

        results.append(lead)

    return results


def update_lead_stage(lead_id: str, new_stage: str, note: str = "") -> bool:
    if new_stage not in LEAD_STAGES:
        return False
    leads = _load_leads()
    for lead in leads:
        if lead["id"] == lead_id:
            lead["stage"] = new_stage
            lead["updated_at"] = datetime.now().isoformat()
            if note:
                lead["notes"].append({
                    "text": note,
                    "timestamp": datetime.now().isoformat(),
                    "stage_change": new_stage,
                })
            _save_leads(leads)
            return True
    return False


def add_note(lead_id: str, note: str) -> bool:
    leads = _load_leads()
    for lead in leads:
        if lead["id"] == lead_id:
            lead["notes"].append({"text": note, "timestamp": datetime.now().isoformat()})
            lead["updated_at"] = datetime.now().isoformat()
            _save_leads(leads)
            return True
    return False


def add_tag(lead_id: str, tag: str) -> bool:
    leads = _load_leads()
    for lead in leads:
        if lead["id"] == lead_id:
            if tag not in lead.get("tags", []):
                lead.setdefault("tags", []).append(tag)
                lead["updated_at"] = datetime.now().isoformat()
                _save_leads(leads)
            return True
    return False


def record_campaign(lead_id: str, campaign_id: str, email_type: str) -> bool:
    leads = _load_leads()
    for lead in leads:
        if lead["id"] == lead_id:
            lead.setdefault("campaigns", []).append({
                "campaign_id": campaign_id,
                "email_type": email_type,
                "sent_at": datetime.now().isoformat(),
            })
            if lead["stage"] == "new":
                lead["stage"] = "contacted"
            lead["updated_at"] = datetime.now().isoformat()
            _save_leads(leads)
            return True
    return False


def opt_out(email: str) -> bool:
    optouts = _load_optouts()
    if email.lower() not in [o.lower() for o in optouts]:
        optouts.append(email.lower())
        _save_optouts(optouts)
    return True


def is_opted_out(email: str) -> bool:
    optouts = _load_optouts()
    return email.lower() in [o.lower() for o in optouts]


# ═══════════════════════════════════════════════════════════════
#  BIN / TRASH SYSTEM
# ═══════════════════════════════════════════════════════════════

def _load_bin() -> List[Dict]:
    if BIN_FILE.exists():
        with open(BIN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_bin(bin_leads: List[Dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(BIN_FILE, "w", encoding="utf-8") as f:
        json.dump(bin_leads, f, indent=2, ensure_ascii=False, default=str)


def move_to_bin(lead_id: str) -> bool:
    """Soft-delete: move a lead from leads.json to bin.json."""
    leads = _load_leads()
    bin_leads = _load_bin()
    target = None
    remaining = []
    for lead in leads:
        if lead["id"] == lead_id:
            target = lead
        else:
            remaining.append(lead)
    if not target:
        return False
    target["deleted_at"] = datetime.now().isoformat()
    bin_leads.insert(0, target)
    _save_leads(remaining)
    _save_bin(bin_leads)
    return True


def get_bin_leads() -> List[Dict]:
    """Return all leads currently in the bin."""
    return _load_bin()


def restore_from_bin(lead_id: str) -> bool:
    """Restore a lead from the bin back to leads.json."""
    bin_leads = _load_bin()
    leads = _load_leads()
    target = None
    remaining = []
    for lead in bin_leads:
        if lead["id"] == lead_id:
            target = lead
        else:
            remaining.append(lead)
    if not target:
        return False
    target.pop("deleted_at", None)
    target["updated_at"] = datetime.now().isoformat()
    leads.insert(0, target)
    _save_leads(leads)
    _save_bin(remaining)
    return True


def permanent_delete(lead_id: str) -> bool:
    """Permanently delete a lead from the bin."""
    bin_leads = _load_bin()
    remaining = [l for l in bin_leads if l["id"] != lead_id]
    if len(remaining) == len(bin_leads):
        return False
    _save_bin(remaining)
    return True


def empty_bin() -> int:
    """Permanently delete ALL leads in the bin. Returns count deleted."""
    bin_leads = _load_bin()
    count = len(bin_leads)
    _save_bin([])
    return count


def get_pipeline_stats() -> Dict:
    leads = _load_leads()
    bin_leads = _load_bin()
    stats = {stage: 0 for stage in LEAD_STAGES}
    countries = {}
    industries = {}

    for lead in leads:
        stats[lead.get("stage", "new")] = stats.get(lead.get("stage", "new"), 0) + 1
        country_val = str(lead.get("country") or "").strip()
        country = country_val if country_val else "Unknown"
        countries[country] = countries.get(country, 0) + 1
        
        industry_val = str(lead.get("industry") or "").strip()
        industry = industry_val if industry_val else "Unknown"
        industries[industry] = industries.get(industry, 0) + 1

    return {
        "total_leads": len(leads),
        "by_stage": stats,
        "by_country": dict(sorted(countries.items(), key=lambda x: -x[1])),
        "by_industry": dict(sorted(industries.items(), key=lambda x: -x[1])),
        "with_contacts": sum(1 for l in leads if l.get("contacts")),
        "with_email": sum(1 for l in leads if any(c.get("email") for c in l.get("contacts", []))),
        "in_bin": len(bin_leads),
    }
