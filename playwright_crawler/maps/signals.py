from typing import Dict, List


AGENCY_KEYWORDS = {
    "marketing",
    "digital",
    "crm",
    "hubspot",
    "automation",
    "revops",
    "revenue operations",
    "inbound",
    "web development",
    "systems integration",
    "branding",
    "advertising",
    "growth",
}


def score_detail(detail: Dict) -> Dict:
    signals: List[str] = []
    is_marketing = False
    is_small = False
    looks_hubspot = False
    score = 0

    categories = [c.lower() for c in detail.get("categories", [])]
    description = (detail.get("description") or "").lower()
    tags = [t.lower() for t in detail.get("tags", [])]

    for cat in categories:
        if "marketing" in cat or "consultant" in cat or "agency" in cat:
            is_marketing = True
            signals.append("Marketing agency category")
            score += 40
        if "software" in cat or "development" in cat:
            signals.append("Software/dev category")
            score += 15

    for kw in AGENCY_KEYWORDS:
        if kw in description or any(kw in t for t in tags):
            score += 10
            signals.append(f"Keyword: {kw}")
            if kw in {"hubspot", "crm", "revops", "automation"}:
                looks_hubspot = True

    reviews = detail.get("reviewsCount") or 0
    if reviews and reviews < 50:
        is_small = True
        signals.append("Low review volume (small agency heuristic)")
        score += 10
    elif reviews and reviews < 200:
        score += 5

    if "hubspot" in description:
        looks_hubspot = True
        score += 20

    return {
        "is_marketing_or_revops": is_marketing or looks_hubspot,
        "is_small_agency": is_small,
        "looks_like_hubspot_buyer": looks_hubspot or is_marketing,
        "signals": list(dict.fromkeys(signals)),
        "score": score,
    }
