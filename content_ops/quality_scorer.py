"""
Neo Eco Cleaning — Content Quality Scorer
============================================
Score generated content on clarity, personalization, CTA strength, and brand consistency.
"""

from typing import Dict
import re


def score_content(content: str, content_type: str = "email") -> Dict:
    """
    Score content on multiple quality dimensions.
    Returns scores 0-100 for each dimension and an overall score.
    """
    scores = {}

    # --- Clarity Score ---
    words = content.split()
    word_count = len(words)
    sentences = re.split(r'[.!?]+', content)
    sentence_count = max(len([s for s in sentences if s.strip()]), 1)
    avg_sentence_length = word_count / sentence_count

    clarity = 100
    if avg_sentence_length > 25:
        clarity -= 20
    if avg_sentence_length > 35:
        clarity -= 20

    jargon = ["synergy", "leverage", "paradigm", "holistic", "scalable", "robust",
              "cutting-edge", "world-class", "best-in-class", "game-changing"]
    jargon_count = sum(1 for j in jargon if j in content.lower())
    clarity -= jargon_count * 10

    paragraphs = content.split("\n\n")
    avg_para_length = sum(len(p.split()) for p in paragraphs) / max(len(paragraphs), 1)
    if avg_para_length < 40:
        clarity += 5

    scores["clarity"] = max(min(clarity, 100), 0)

    # --- Length Score ---
    ideal_lengths = {
        "email": (100, 180),
        "case_study": (300, 800),
        "linkedin_post": (50, 200),
        "blog_post": (500, 1500),
        "catalog_entry": (50, 150),
    }
    min_len, max_len = ideal_lengths.get(content_type, (100, 500))

    if min_len <= word_count <= max_len:
        scores["length"] = 100
    elif word_count < min_len * 0.5 or word_count > max_len * 1.5:
        scores["length"] = 30
    elif word_count < min_len or word_count > max_len:
        scores["length"] = 65
    else:
        scores["length"] = 80

    # --- Specificity Score ---
    specificity = 0

    numbers = re.findall(r'\d+', content)
    specificity += min(len(numbers) * 15, 40)

    specific_terms = ["eco", "eco-friendly", "survey", "quote", "guarantee", "%",
                      "£", "North London", "block", "communal", "stairwell",
                      "Rendall", "MVN", "Hilton", "property"]
    for term in specific_terms:
        if term.lower() in content.lower():
            specificity += 5

    scores["specificity"] = min(specificity, 100)

    # --- CTA Score ---
    cta_phrases = [
        "survey", "quote", "reply", "interested",
        "discuss", "schedule", "book", "meeting", "call",
        "contact", "reach out", "get in touch", "free",
    ]
    cta_count = sum(1 for phrase in cta_phrases if phrase in content.lower())

    if cta_count >= 2:
        scores["cta_strength"] = 100
    elif cta_count == 1:
        scores["cta_strength"] = 75
    else:
        scores["cta_strength"] = 20

    last_section = content[int(len(content) * 0.8):]
    has_end_cta = any(p in last_section.lower() for p in cta_phrases)
    if has_end_cta:
        scores["cta_strength"] = min(scores["cta_strength"] + 15, 100)

    # --- Brand Consistency Score ---
    brand_terms = [
        "neo eco", "eco-friendly", "cleaning", "block", "north london",
        "property", "communal", "sustainable", "eco", "green",
    ]
    brand_hits = sum(1 for term in brand_terms if term in content.lower())
    scores["brand_consistency"] = min(brand_hits * 12, 100)

    # --- Tone Score ---
    aggressive = ["buy now", "limited time", "don't miss", "act now", "hurry",
                  "exclusive deal", "once in a lifetime"]
    aggressive_count = sum(1 for a in aggressive if a in content.lower())

    warm_phrases = ["we'd love", "looking forward", "happy to",
                    "pleased to", "appreciate", "thank", "best regards",
                    "no obligation", "free survey", "quality guarantee"]
    warm_count = sum(1 for w in warm_phrases if w in content.lower())

    tone_score = 70 + (warm_count * 10) - (aggressive_count * 20)
    scores["tone"] = max(min(tone_score, 100), 0)

    # --- Overall Score ---
    weights = {
        "clarity": 0.20,
        "length": 0.15,
        "specificity": 0.20,
        "cta_strength": 0.15,
        "brand_consistency": 0.15,
        "tone": 0.15,
    }
    overall = sum(scores.get(k, 0) * w for k, w in weights.items())
    scores["overall"] = round(overall, 1)

    # --- Grade & Recommendations ---
    if overall >= 90:
        scores["grade"] = "A+"
        scores["verdict"] = "Excellent — ready to send"
    elif overall >= 80:
        scores["grade"] = "A"
        scores["verdict"] = "Good — minor polish recommended"
    elif overall >= 70:
        scores["grade"] = "B"
        scores["verdict"] = "Decent — review before sending"
    elif overall >= 60:
        scores["grade"] = "C"
        scores["verdict"] = "Needs improvement before sending"
    else:
        scores["grade"] = "D"
        scores["verdict"] = "Significant revision needed"

    recs = []
    if scores["clarity"] < 70:
        recs.append("Shorten sentences and remove jargon for better clarity")
    if scores["length"] < 70:
        recs.append(f"Adjust length ({word_count} words) — ideal is {min_len}-{max_len} words")
    if scores["specificity"] < 60:
        recs.append("Add specific numbers, client references, or eco-friendly details")
    if scores["cta_strength"] < 70:
        recs.append("Add a clear call-to-action near the end (free survey, quote, etc.)")
    if scores["brand_consistency"] < 60:
        recs.append("Include more brand terms: eco-friendly, North London, block cleaning, etc.")
    if scores["tone"] < 70:
        recs.append("Soften the tone — less salesy, more consultative")

    scores["recommendations"] = recs
    scores["word_count"] = word_count

    return scores
