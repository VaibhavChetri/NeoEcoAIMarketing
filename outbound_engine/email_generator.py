"""
Neo Eco Cleaning — AI Email Generator (Gemini Pro)
=====================================================
Generate personalized cold emails for property management leads
using Google Gemini Pro. Supports multiple email types:
cold outreach, follow-ups, free quote offers, breakup emails.
"""

import json
import os
import yaml
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "neo_eco_config.yaml"
CASE_STUDIES_FILE = BASE_DIR / "data" / "case_studies.json"
PRODUCTS_FILE = BASE_DIR / "data" / "products.json"
OUTPUT_DIR = BASE_DIR / "output" / "emails"

# Load environment
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env", override=True)


# Try to import Google GenAI
try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


def _load_config() -> Dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_case_studies() -> List[Dict]:
    if CASE_STUDIES_FILE.exists():
        with open(CASE_STUDIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _load_products() -> List[Dict]:
    if PRODUCTS_FILE.exists():
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("products", data) if isinstance(data, dict) else data
    return []


def _get_gemini_client() -> Optional[object]:
    """Initialize Google Gemini client."""
    if not HAS_GEMINI:
        return None
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your"):
        return None
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception:
        return None


def _get_season() -> str:
    month = datetime.now().month
    if month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    elif month in [9, 10, 11]:
        return "Autumn"
    return "Winter"


def _build_system_prompt(config: Dict) -> str:
    """Build the LLM system prompt from Neo Eco config."""
    company = config.get("company", {})
    vp = config.get("value_proposition", {})
    guidelines = config.get("content_guidelines", {})
    products = _load_products()

    service_summary = "\n".join(
        f"  - {p['name']}: {p.get('pricing_range_gbp', p.get('price_range_usd', 'N/A'))}, "
        f"Response: {p.get('lead_time_days', 'N/A')} days"
        for p in products[:6]
    )

    case_studies = _load_case_studies()
    cs_summary = "\n".join(
        f"  - {cs['title']}: {cs['results'].get('quality', 'N/A')}, "
        f"{cs['results'].get('delivery', 'N/A')}"
        for cs in case_studies[:3]
    )

    named_clients = vp.get("named_clients", [])
    client_summary = "\n".join(
        f"  - {c['name']} ({c['credential']}) — {c['service']}"
        for c in named_clients
    )

    return f"""You are an expert email copywriter for {company.get('name', 'Neo Eco Cleaning')}.
Industry: {company.get('industry', 'Professional Eco-Friendly Cleaning Services')}
Target market: {company.get('target_market', 'Property Managers & Building Management Companies in North London')}

VALUE PROPOSITION:
{vp.get('main_message', '')}

KEY BENEFITS:
{chr(10).join('  - ' + b for b in vp.get('key_benefits', []))}

DIFFERENTIATORS:
{chr(10).join('  - ' + d for d in vp.get('differentiators', []))}

PAIN POINTS WE SOLVE:
{chr(10).join('  - ' + p for p in vp.get('pain_points_addressed', []))}

OUR SERVICES:
{service_summary}

NAMED CLIENTS (use these as social proof):
{client_summary}

CASE STUDIES:
{cs_summary}

WRITING GUIDELINES:
- Tone: {guidelines.get('tone', 'Professional, warm, and environmentally conscious')}
- Max length: {guidelines.get('max_word_count', 350)} words
- AVOID: {', '.join(guidelines.get('avoid', []))}
- INCLUDE: {', '.join(guidelines.get('include', []))}

IMPORTANT RULES:
1. Always write in first person PLURAL ("we", "our", "us") as the team at {company.get('name', 'Neo Eco Cleaning')}. Say "we are at Neo Eco Cleaning" — NEVER say "I'm [Name] from Neo Eco Cleaning" or use any personal name introduction.
2. ALWAYS reference named clients: Rendall & Rittner (Property Manager of the Year 2024) and MVN Block Management — these are our strongest selling points.
3. Emphasise our eco-friendly approach with specific details (100% eco products, no toxic chemicals).
4. Reference North London expertise specifically.
5. Keep emails between 250-350 words — long enough to be complete, short enough to be readable.
6. NEVER cut off mid-sentence. Every sentence MUST be complete. This is NON-NEGOTIABLE.
7. Sound human, not robotic — no buzzwords or corporate jargon.
8. Always include service recommendations as bullet points with proper spacing.
9. The email MUST end with the mandatory closing paragraph (see below) — NEVER omit it.
"""


EMAIL_TYPE_PROMPTS = {
    "cold_outreach": """Write a deeply personalized cold outreach email to {contact_name} at {company_name}.

=== TARGET COMPANY PROFILE ===
Company: {company_name}
Company Description: {about}
Area: {country}
Industry: {industry}
Employees: {employees}
Revenue: {revenue}
Founded: {founded}

=== OUR FULL SERVICE CATALOG ===
{product_recommendations}

=== NEO ECO CLEANING DIFFERENTIATORS ===
Many property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. We solve all three:
- 100% eco-friendly cleaning products — no toxic chemicals
- Ex-Hilton Hotel trained staff — 5-star cleaning standards
- Quality Guarantee — all complaints resolved at no additional cost
- Trusted by Rendall & Rittner (Property Manager of the Year 2024) and MVN Block Management
- North London specialists with dedicated local teams

CRITICAL PERSONALIZATION RULES:
1. You MUST read the Company Description above carefully and reference SPECIFIC details about their company (e.g., their property portfolio, areas they cover, types of properties they manage).
2. Based on the Company Description, identify which of our services are MOST RELEVANT to what this company needs. For example, if they manage residential blocks, recommend block cleaning. If they are estate agents, recommend end-of-tenancy cleaning.
3. List 2-3 of our most relevant services as BULLET POINTS. Each bullet MUST be on its own line with a BLANK LINE between bullets. Each bullet should include: service name, key benefit, and pricing indicator. Use this EXACT format:

• Block & Communal Cleaning — weekly scheduled cleans from £150/month, includes stairwells, lobbies, and bin rooms

• End of Tenancy Cleaning — from £180/property, 24-hour turnaround, meets letting agent standards

• Pressure Washing — from £250/session, eco-friendly external cleaning for car parks and pathways

4. If they manage residential blocks, highlight our Rendall & Rittner and MVN Block Management references.
5. If they are estate agents or letting agents, emphasise our end-of-tenancy service.
6. Always mention our eco-friendly approach and Quality Guarantee.

MANDATORY EMAIL STRUCTURE (follow this order EXACTLY):

SECTION 1 — PERSONALIZED GREETING (1-2 sentences):
If "{contact_name}" is empty, open with just "Hi," (no name). Otherwise open with "Hi {contact_name},". Follow with a sentence referencing something specific about their company from the Company Description.

SECTION 2 — INTRODUCTION + FIT (2-3 sentences):
Introduce using "we are at Neo Eco Cleaning" (NOT "I'm [Name] from Neo Eco Cleaning" — NEVER use personal name introductions). Explain why we are a great fit for their specific needs.

SECTION 3 — COMPANY DIFFERENTIATORS (include this paragraph):
Include a paragraph mentioning that many property managers face challenges with unreliable contractors, inconsistent cleaning standards, and harsh chemicals, and that we solve these with:
• 100% eco-friendly products — no toxic chemicals in shared spaces
• Ex-Hilton Hotel trained staff — hospitality-grade cleaning standards
• Quality Guarantee — complaints resolved at no additional cost
• Trusted by Rendall & Rittner (Property Manager of the Year 2024)

SECTION 4 — SERVICE RECOMMENDATIONS (2-3 bullet points):
Based on what the company manages, recommend 2-3 relevant services from our catalog. Format each as a bullet point with service name, key benefit, and pricing. Put a BLANK LINE between each bullet point.

SECTION 5 — MANDATORY CLOSING (copy this VERBATIM — do NOT change a single word):
We work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.

Would a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote — completely free.

CRITICAL FORMATTING RULES:
- The email MUST be 250-350 words. Do NOT write less than 250 words.
- Write COMPLETE sentences — NEVER cut off mid-sentence. If you run out of space, finish the sentence.
- Put a blank line between each paragraph and between each bullet point.
- Use plain English. NO special characters, NO unicode symbols, NO emojis.
- Use only standard ASCII apostrophes (') and quotes (").
- Do NOT include any sign-off like "Best regards" or "Warm regards" — the email ends after the "completely free" line.
- The last two paragraphs of the email MUST be the mandatory closing text above. This is NON-NEGOTIABLE.

Return a JSON object with:
{{"subject": "email subject line", "body": "email body text (plain text, no HTML)"}}""",

    "follow_up_case_study": """Write a follow-up email to {contact_name} at {company_name}.
We sent them a cold email a few days ago and haven't heard back.
Company info: {about}
Area: {country}

This email should:
- Briefly reference the previous email (don't repeat it)
- Share a relevant case study: Rendall & Rittner (Property Manager of the Year 2024) hired us for block cleaning and saw 90% reduction in tenant complaints
- Keep it shorter than the first email (under 120 words)
- Include a specific number or result to build credibility
- End with a low-pressure CTA (free site survey)

Return a JSON object with:
{{"subject": "email subject line", "body": "email body text (plain text, no HTML)"}}""",

    "follow_up_quote": """Write a 3rd touchpoint email to {contact_name} at {company_name}.
We've emailed twice with no response.
Company info: {about}
Area: {country}

This email should:
- Acknowledge they're busy
- Offer something tangible: a FREE no-obligation site survey and quote
- Mention that our Quality Guarantee means zero risk
- Keep it very short (under 100 words)
- Make it easy to say yes

Return a JSON object with:
{{"subject": "email subject line", "body": "email body text (plain text, no HTML)"}}""",

    "breakup": """Write a "breakup" email to {contact_name} at {company_name}.
This is our 4th and final email — they haven't responded to 3 previous emails.
Company info: {about}
Area: {country}

This email should:
- Be very brief (under 80 words)
- Politely ask permission to close their file
- Leave the door open for future contact
- Use mild reverse psychology ("if now's not the right time...")
- Include our email (priyanka.singh@neoecocleaning.co.uk) for when they're ready

Return a JSON object with:
{{"subject": "email subject line", "body": "email body text (plain text, no HTML)"}}""",
}


def generate_email(
    lead: Dict,
    email_type: str = "cold_outreach",
    custom_prompt: str = "",
    generation_method: str = "ai",
) -> Dict:
    """
    Generate a personalized email for a lead using Gemini Pro.
    Falls back to template-based generation if Gemini is unavailable.
    """
    config = _load_config()
    contact = {}
    if lead.get("contacts"):
        contact = lead["contacts"][0]

    # Generic / non-personal email prefixes — no individual's name available
    GENERIC_EMAIL_PREFIXES = {
        "hello", "contact", "contacts", "sales", "info", "support", "admin",
        "office", "enquiries", "enquiry", "team", "mail", "general",
        "accounts", "billing", "reception", "help", "service", "services",
        "bookings", "booking", "management", "operations", "hr", "jobs",
        "marketing", "media", "press", "feedback", "complaints", "noreply",
        "no-reply", "postmaster", "webmaster",
    }

    # Determine if we have a real person's name
    full_name = contact.get("name", "") or ""
    first_name = full_name.split()[0].strip() if full_name.strip() else ""

    # Check if the email prefix is generic (not a person's name)
    contact_email = contact.get("email", "") or ""
    email_prefix = contact_email.split("@")[0].lower().strip() if "@" in contact_email else ""

    if not first_name or first_name.lower() == "there" or email_prefix in GENERIC_EMAIL_PREFIXES:
        first_name = ""

    # Build service recommendations based on the company's profile
    products = _load_products()
    about_text = lead.get("about", "") or ""
    industry_text = lead.get("industry", "") or ""
    profile_text = (about_text + " " + industry_text).lower()
    
    product_recs = []
    for p in products:
        product_recs.append(
            f"- {p['name']} ({p['category']}): {p.get('pricing_range_gbp', p.get('price_range_usd', 'N/A'))}, "
            f"Response: {p.get('lead_time_days', 'N/A')} days, "
            f"Includes: {', '.join(p.get('customization', [])[:3])}, "
            f"Eco: {', '.join(p.get('fabrics', [])[:2])}"
        )
    product_recommendations = "\n".join(product_recs) if product_recs else "Full service catalog available on request."

    context = {
        "company_name": lead.get("company_name", "your company"),
        "contact_name": first_name,
        "about": about_text[:800] if about_text else "No company details available — write a general but professional email.",
        "country": lead.get("country", "North London"),
        "industry": lead.get("industry", "Property Management"),
        "employees": lead.get("employees", ""),
        "revenue": lead.get("revenue", ""),
        "founded": lead.get("founded", ""),
        "season": _get_season(),
        "product_recommendations": product_recommendations,
    }

    if generation_method == "template":
        return _generate_from_template(config, context, email_type)

    client = _get_gemini_client()
    if not client:
        fallback = _generate_from_template(config, context, email_type)
        fallback["error"] = "Gemini API key is not configured or invalid."
        return fallback

    result = _generate_with_gemini(client, config, context, email_type, custom_prompt)
    if result.get("error"):
        fallback = _generate_from_template(config, context, email_type)
        fallback["error"] = result["error"]
        return fallback

    return result


def _generate_with_gemini(
    client, config: Dict, context: Dict, email_type: str, custom_prompt: str
) -> Dict:
    """Generate email using Google Gemini Pro."""
    system_prompt = _build_system_prompt(config)

    if custom_prompt:
        user_prompt = custom_prompt.format(**context)
    elif email_type in EMAIL_TYPE_PROMPTS:
        user_prompt = EMAIL_TYPE_PROMPTS[email_type].format(**context)
    else:
        user_prompt = EMAIL_TYPE_PROMPTS["cold_outreach"].format(**context)

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Mandatory closing text — always appended if missing
    MANDATORY_CLOSING = (
        "\n\nWe work with property managers and building management companies across North London, "
        "and we'd love to explore if we could help maintain the highest standards across your portfolio."
        "\n\nWould a free, no-obligation site survey work this week? We can assess your "
        "requirements and provide a tailored quote — completely free."
    )

    try:
        # Build the full prompt with system instructions + user request
        full_prompt = f"""{system_prompt}

---

{user_prompt}

IMPORTANT: You MUST respond with ONLY a valid JSON object. No markdown, no code fences, no extra text.
Use escaped newlines (\\n) inside string values. Example format:
{{"subject": "Subject line here", "body": "Line 1\\n\\nLine 2\\n\\nLine 3"}}"""

        # Disable thinking so all output tokens go to the actual email content
        try:
            from google.genai import types
            gen_config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )
        except (ImportError, AttributeError):
            gen_config = {
                "temperature": 0.7,
                "max_output_tokens": 8192,
            }

        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=gen_config,
        )

        content = response.text.strip()
        # Fix encoding: replace common unicode issues with ASCII equivalents
        content = content.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
        content = content.replace("\u2013", "-").replace("\u2014", "-").replace("\u2026", "...").replace("\u00a0", " ")
        content = content.replace("\xe2\x80\x99", "'").replace("\xe2\x80\x93", "-")

        # Clean up response — remove markdown code fences if present
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

        # Try parsing with fixes for common AI JSON mistakes
        def try_parse(text):
            text = text.replace("\\'", "'")
            try:
                return json.loads(text)
            except Exception as e:
                # If it's truncated, try appending closing braces/quotes
                if "Unterminated string" in str(e) or "Expecting ',' delimiter" in str(e) or "Expecting property name" in str(e):
                    for suffix in ['"}', '"}', '}']:
                        try:
                            return json.loads(text + suffix)
                        except:
                            pass
                
                # Try replacing raw newlines with \\n
                text_no_nl = text.replace("\n", "\\n")
                try:
                    return json.loads(text_no_nl)
                except:
                    pass
                
                raise e

        try:
            result = try_parse(content)
        except Exception:
            # Absolute last resort: regex
            subj_match = re.search(r'"subject"\s*:\s*"([^"]*)"', content, re.DOTALL)
            body_match = re.search(r'"body"\s*:\s*"([\s\S]*?)("?\s*\}|$)', content, re.DOTALL)
            
            if subj_match:
                body_text = body_match.group(1).strip() if body_match else ""
                
                # Fix unicode escapes
                try:
                    body_text = body_text.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass
                    
                body_text = body_text.replace('\\n', '\n').replace('\\"', '"')
                
                subj_text = subj_match.group(1).strip()
                try:
                    subj_text = subj_text.encode('utf-8').decode('unicode_escape')
                except Exception:
                    pass
                    
                result = {"subject": subj_text, "body": body_text}
            else:
                result = None

        if not result:
            raise ValueError(f"Could not parse Gemini response as JSON: {content[:300]}")

        # Post-processing: ensure the mandatory closing is always present
        body = result.get("body", "")
        if "completely free" not in body.lower():
            # The mandatory closing was cut off — append it
            body = body.rstrip()
            # Clean up any incomplete sentence at the end
            if body and not body[-1] in '.!?:':
                # Find the last complete sentence
                last_period = max(body.rfind('.'), body.rfind('!'), body.rfind('?'))
                if last_period > len(body) * 0.5:  # Only trim if we'd keep at least half
                    body = body[:last_period + 1]
            body += MANDATORY_CLOSING
            result["body"] = body

        return {
            "subject": result.get("subject", ""),
            "body": result.get("body", ""),
            "email_type": email_type,
            "model": model,
            "generated_at": datetime.now().isoformat(),
            "company_name": context["company_name"],
            "contact_name": context["contact_name"],
            "ai_generated": True,
            "tokens_used": 0,
        }
    except Exception as e:
        return {
            "error": f"Gemini API Error: {str(e)}",
            "email_type": email_type,
            "ai_generated": False,
        }


def _generate_from_template(config: Dict, context: Dict, email_type: str) -> Dict:
    """Fallback: generate email from templates when AI is unavailable."""
    company = config.get("company", {})
    vp = config.get("value_proposition", {})

    templates = {
        "cold_outreach": {
            "subject": f"{context['company_name']} — Eco-Friendly Block Cleaning for Your Properties",
            "body": f"""Hi{(' ' + context['contact_name']) if context['contact_name'] else ''},

I came across {context['company_name']} and was impressed by your presence in the {context['country']} property management market.

Many property managers face challenges with unreliable cleaning contractors, inconsistent standards, and the use of harsh chemicals in shared residential spaces. At Neo Eco Cleaning, we solve all three:

• 100% eco-friendly cleaning products — no toxic chemicals in shared spaces

• Ex-Hilton Hotel trained staff — hospitality-grade cleaning standards

• Quality Guarantee — all complaints resolved at no additional cost

• Trusted by Rendall & Rittner (Property Manager of the Year 2024) and MVN Block Management

Based on your portfolio, we think these services could be particularly relevant:

• Block & Communal Cleaning — weekly scheduled cleans from £150/month, includes stairwells, lobbies, and bin rooms

• End of Tenancy Cleaning — from £180/property, 24-hour turnaround, meets letting agent standards

We work with property managers and building management companies across North London, and we'd love to explore if we could help maintain the highest standards across your portfolio.

Would a free, no-obligation site survey work this week? We can assess your requirements and provide a tailored quote — completely free.""",
        },
        "follow_up_case_study": {
            "subject": f"How Rendall & Rittner reduced tenant complaints by 90% — could we help {context['company_name']}?",
            "body": f"""Hi{(' ' + context['contact_name']) if context['contact_name'] else ''},

Following up on my previous note. I wanted to share a quick result:

Rendall & Rittner (Property Manager of the Year 2024) came to us after their previous cleaning contractor was inconsistent and generating tenant complaints. Since switching to Neo Eco Cleaning, they've seen a 90% reduction in cleaning-related complaints and zero missed scheduled cleans in 12 months.

Would love to discuss how we could achieve similar results for {context['company_name']}. Shall I arrange a free site survey?""",
        },
        "follow_up_quote": {
            "subject": f"Free site survey for {context['company_name']} — no strings attached",
            "body": f"""Hi{(' ' + context['contact_name']) if context['contact_name'] else ''},

I know you're busy, so I'll keep this brief.

I'd like to offer you a completely free, no-obligation site survey of your properties. We'll assess your cleaning requirements and provide a tailored quote — with zero commitment.

Our Quality Guarantee means if you're ever unhappy, we resolve it at no extra cost.

Interested? Just reply and we'll arrange a convenient time.""",
        },
        "breakup": {
            "subject": f"Should I close your file{(', ' + context['contact_name']) if context['contact_name'] else ''}?",
            "body": f"""Hi{(' ' + context['contact_name']) if context['contact_name'] else ''},

I've reached out a few times and haven't heard back, which I completely understand — timing is everything.

I don't want to be a bother, so I'll close your file for now.

If cleaning ever becomes a priority — whether it's finding a more reliable block cleaning contractor, switching to eco-friendly products, or needing a deep clean — my inbox is always open at priyanka.singh@neoecocleaning.co.uk.

Wishing {context['company_name']} continued success.""",
        },
    }

    template = templates.get(email_type, templates["cold_outreach"])

    return {
        "subject": template["subject"],
        "body": template["body"],
        "email_type": email_type,
        "model": "template",
        "generated_at": datetime.now().isoformat(),
        "company_name": context["company_name"],
        "contact_name": context["contact_name"],
        "ai_generated": False,
        "tokens_used": 0,
    }


def generate_campaign_emails(
    leads: List[Dict],
    email_type: str = "cold_outreach",
    campaign_id: str = "",
) -> List[Dict]:
    """Generate emails for a list of leads."""
    if not campaign_id:
        campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    emails = []
    for i, lead in enumerate(leads):
        print(f"  [{i+1}/{len(leads)}] Generating email for {lead.get('company_name', 'Unknown')}...")
        email = generate_email(lead, email_type)
        email["campaign_id"] = campaign_id
        email["lead_id"] = lead.get("id", "")
        emails.append(email)

    # Save generated emails
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{campaign_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Generated {len(emails)} emails → {output_file}")
    return emails


def score_email(email: Dict) -> Dict:
    """Score an email on quality metrics."""
    body = email.get("body", "")
    subject = email.get("subject", "")
    scores = {}

    # Length score (ideal: 100-180 words)
    word_count = len(body.split())
    if 100 <= word_count <= 180:
        scores["length"] = 100
    elif 80 <= word_count <= 200:
        scores["length"] = 80
    elif word_count < 50 or word_count > 300:
        scores["length"] = 40
    else:
        scores["length"] = 60

    # Personalization score
    company_name = email.get("company_name", "")
    contact_name = email.get("contact_name", "")
    personalization = 0
    if company_name and company_name.lower() in body.lower():
        personalization += 40
    if contact_name and contact_name.lower() != "there" and contact_name.lower() in body.lower():
        personalization += 30
    if any(term in body.lower() for term in ["rendall", "mvn", "eco-friendly", "quality guarantee", "north london"]):
        personalization += 30
    scores["personalization"] = min(personalization, 100)

    # CTA score
    cta_phrases = ["survey", "quote", "call", "reply", "interested", "discuss", "schedule", "free"]
    has_cta = any(phrase in body.lower() for phrase in cta_phrases)
    scores["cta_clarity"] = 100 if has_cta else 30

    # Subject line score
    subject_len = len(subject)
    if 30 <= subject_len <= 60:
        scores["subject_line"] = 100
    elif 20 <= subject_len <= 80:
        scores["subject_line"] = 70
    else:
        scores["subject_line"] = 40

    # Overall score
    weights = {"length": 0.25, "personalization": 0.35, "cta_clarity": 0.20, "subject_line": 0.20}
    overall = sum(scores[k] * weights[k] for k in weights)
    scores["overall"] = round(overall, 1)

    return scores
