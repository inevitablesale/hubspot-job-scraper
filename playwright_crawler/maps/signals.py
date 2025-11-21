from typing import Dict, List


KEYWORD_SIGNALS = {
    "marketing": (15, "Marketing keyword"),
    "digital": (10, "Digital keyword"),
    "crm": (25, "CRM keyword"),
    "hubspot": (35, "HubSpot keyword"),
    "automation": (20, "Automation keyword"),
    "revops": (25, "RevOps keyword"),
    "revenue operations": (20, "Revenue ops keyword"),
    "inbound": (15, "Inbound keyword"),
    "web development": (15, "Web dev keyword"),
    "systems integration": (15, "Integration keyword"),
    "branding": (10, "Branding keyword"),
    "advertising": (10, "Advertising keyword"),
    "growth": (10, "Growth keyword"),
}


def _is_marketing_category(cat: str) -> bool:
    cat = cat.lower()
    keywords = [
        "marketing",
        "consult",
        "revops",
        "crm",
        "digital",
        "advertising",
        "inbound",
        "growth",
        "demand",
    ]
    return any(k in cat for k in keywords)


NON_TARGET_CATEGORIES = [
    "equipment",
    "rental",
    "construction",
    "storage",
    "automotive",
    "plumbing",
    "hvac",
    "landscaping",
    "cleaning",
]


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
        if any(block in cat for block in NON_TARGET_CATEGORIES):
            signals.append("Non-marketing category")
            continue
        if _is_marketing_category(cat):
            is_marketing = True
            signals.append("Marketing/consulting category")
            score += 40
        if "agency" in cat and _is_marketing_category(cat):
            signals.append("Agency (marketing-aligned)")
            score += 10
        if "software" in cat or "development" in cat:
            signals.append("Software/dev category")
            score += 15

    for kw, (points, label) in KEYWORD_SIGNALS.items():
        if kw in description or any(kw in t for t in tags):
            score += points
            signals.append(label)
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

    # If we never found a marketing/RevOps/HubSpot signal, cap the score so
    # generic agencies (e.g., equipment rental) cannot surface as high-value.
    if not (is_marketing or looks_hubspot):
        score = min(score, 20)
        signals.append("Capped: not marketing/RevOps aligned")

    score = min(score, 200)

    return {
        "is_marketing_or_revops": is_marketing or looks_hubspot,
        "is_small_agency": is_small,
        "looks_like_hubspot_buyer": looks_hubspot or is_marketing,
        "signals": list(dict.fromkeys(signals)),
        "score": score,
    }
