from typing import Dict, Optional

from ..utils import normalize_domain


def to_candidate(detail: Dict, signal_payload: Dict) -> Optional[Dict]:
    website = detail.get("website")
    domain = normalize_domain(website) if website else None
    if not domain:
        return None
    signals = (signal_payload.get("signals") or []) + detail.get("tags", [])
    return {
        "domain": domain,
        "company": detail.get("title") or domain,
        "categoryName": detail.get("categories", [None])[0],
        "raw_website": website,
        "maps_url": detail.get("maps_url"),
        "signals": list(dict.fromkeys([s for s in signals if s])),
        "score": signal_payload.get("score", 0),
    }
