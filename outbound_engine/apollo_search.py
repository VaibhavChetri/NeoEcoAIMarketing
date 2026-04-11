"""
Neo Eco Cleaning — Apollo.io Search
=====================================
Search for property management and building management leads via Apollo.io.
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")
APOLLO_BASE_URL = "https://api.apollo.io/v1"
OUTPUT_DIR = BASE_DIR / "output" / "apollo"


def search_organizations(
    keyword: str = "property management",
    locations: List[str] = None,
    min_employees: int = 1,
    max_employees: int = 500,
    per_page: int = 25,
    page: int = 1,
) -> Dict:
    """Search for organizations on Apollo.io."""
    if not APOLLO_API_KEY or APOLLO_API_KEY.startswith("your"):
        return {"error": "Apollo API key not configured. Add APOLLO_API_KEY to .env"}

    if locations is None:
        locations = ["London, United Kingdom", "North London, United Kingdom"]

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    payload = {
        "api_key": APOLLO_API_KEY,
        "q_organization_keyword_tags": [keyword],
        "organization_locations": locations,
        "organization_num_employees_ranges": [f"{min_employees},{max_employees}"],
        "per_page": per_page,
        "page": page,
    }

    try:
        response = requests.post(
            f"{APOLLO_BASE_URL}/mixed_companies/search",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        companies = []
        for org in data.get("organizations", []):
            companies.append({
                "apollo_id": org.get("id", ""),
                "company_name": org.get("name", ""),
                "website": org.get("website_url", ""),
                "industry": org.get("industry", ""),
                "employees": org.get("estimated_num_employees", ""),
                "country": org.get("country", ""),
                "city": org.get("city", ""),
                "about": org.get("short_description", ""),
                "linkedin_url": org.get("linkedin_url", ""),
                "phone": org.get("phone", ""),
                "founded": org.get("founded_year", ""),
                "revenue": org.get("annual_revenue_printed", ""),
            })

        return {
            "total_results": data.get("pagination", {}).get("total_entries", 0),
            "page": page,
            "per_page": per_page,
            "companies": companies,
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Apollo API error: {str(e)}"}


def search_people(
    organization_ids: List[str] = None,
    titles: List[str] = None,
    locations: List[str] = None,
    per_page: int = 25,
    page: int = 1,
) -> Dict:
    """Search for people/contacts on Apollo.io."""
    if not APOLLO_API_KEY or APOLLO_API_KEY.startswith("your"):
        return {"error": "Apollo API key not configured"}

    if titles is None:
        titles = [
            "Property Manager", "Building Manager", "Facilities Manager",
            "Managing Agent", "Estate Manager", "Director",
            "Operations Manager", "Contracts Manager",
        ]

    if locations is None:
        locations = ["London, United Kingdom"]

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    payload = {
        "api_key": APOLLO_API_KEY,
        "person_titles": titles,
        "person_locations": locations,
        "per_page": per_page,
        "page": page,
    }

    if organization_ids:
        payload["organization_ids"] = organization_ids

    try:
        response = requests.post(
            f"{APOLLO_BASE_URL}/mixed_people/search",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        contacts = []
        for person in data.get("people", []):
            contacts.append({
                "apollo_id": person.get("id", ""),
                "name": person.get("name", ""),
                "email": person.get("email", ""),
                "title": person.get("title", ""),
                "linkedin_url": person.get("linkedin_url", ""),
                "phone": person.get("phone_number", ""),
                "company_name": person.get("organization", {}).get("name", ""),
                "company_website": person.get("organization", {}).get("website_url", ""),
                "city": person.get("city", ""),
                "country": person.get("country", ""),
            })

        return {
            "total_results": data.get("pagination", {}).get("total_entries", 0),
            "page": page,
            "per_page": per_page,
            "contacts": contacts,
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Apollo API error: {str(e)}"}


def enrich_company(domain: str) -> Dict:
    """Enrich a company by domain."""
    if not APOLLO_API_KEY or APOLLO_API_KEY.startswith("your"):
        return {"error": "Apollo API key not configured"}

    try:
        response = requests.post(
            f"{APOLLO_BASE_URL}/organizations/enrich",
            json={"api_key": APOLLO_API_KEY, "domain": domain},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("organization", {})
    except Exception as e:
        return {"error": str(e)}


def export_to_excel(results: List[Dict], filename: str = "") -> str:
    """Export search results to Excel."""
    try:
        import pandas as pd
    except ImportError:
        return "pandas not installed"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = f"apollo_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    filepath = OUTPUT_DIR / filename
    df = pd.DataFrame(results)
    df.to_excel(filepath, index=False, engine="openpyxl")
    return str(filepath)


def get_default_icp_params() -> Dict:
    """Get default ICP search parameters for Neo Eco Cleaning."""
    return {
        "keywords": [
            "property management",
            "block management",
            "building management",
            "estate agent",
            "letting agent",
            "facilities management",
        ],
        "locations": [
            "London, United Kingdom",
            "North London, United Kingdom",
            "Barnet, United Kingdom",
            "Enfield, United Kingdom",
            "Camden, United Kingdom",
            "Islington, United Kingdom",
            "Hertfordshire, United Kingdom",
        ],
        "titles": [
            "Property Manager",
            "Building Manager",
            "Facilities Manager",
            "Estate Manager",
            "Managing Agent",
            "Director",
            "Operations Manager",
            "Contracts Manager",
            "Head of Property",
        ],
        "min_employees": 1,
        "max_employees": 500,
    }
