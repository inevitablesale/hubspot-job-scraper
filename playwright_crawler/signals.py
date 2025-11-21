import os
from typing import List, Tuple, Dict, Optional

HUBSPOT_TECH_KEYWORDS = [
    "hubspot",
    "hub spot",
    "crm",
    "workflows",
    "integrations",
    "cms hub",
    "marketing hub",
    "service hub",
    "operations hub",
    "inbound",
    "reports",
    "dashboard",
    "dashboards",
    "portal",
    "map properties",
    "api",
    "private app token",
]

HUBSPOT_STRONG_SIGNALS = [
    "hubspot certified",
    "hubspot certification",
    "hubspot partner",
    "hubspot elite partner",
    "hubspot gold partner",
    "operations hub",
    "hubdb",
    "serverless functions",
    "custom object",
]

CONSULTANT_INTENT = [
    "hubspot consultant",
    "crm consultant",
    "revops consultant",
    "marketing ops",
    "mops",
    "solutions architect",
    "hubspot onboarding",
    "hubspot implementation",
    "hubspot specialist",
    "revops specialist",
    "workflow automation",
]

DEVELOPER_INTENT = [
    "hubspot developer",
    "hubspot cms developer",
    "hubspot theme",
    "hubspot custom modules",
    "hubspot serverless",
    "hubspot api",
    "hubspot integrations",
    "nodejs hubspot",
    "python hubspot api",
]

SENIOR_CONSULTANT_INTENT = [
    "senior consultant",
    "lead consultant",
    "principal consultant",
]

ARCHITECT_INTENT = [
    "solutions architect",
    "revops architect",
    "technical architect",
    "systems architect",
]

ROLE_FILTER = {
    r.strip()
    for r in os.getenv("ROLE_FILTER", "").split(",")
    if r.strip()
}
REMOTE_ONLY = os.getenv("REMOTE_ONLY", "false").lower() == "true"
ALLOW_AGENCIES = os.getenv("ALLOW_AGENCIES", "false").lower() == "true"


SignalResult = Dict[str, object]


def _apply_boosters(score: int, signals: List[str], text: str, role: str) -> Tuple[int, str, List[str]]:
    remote = "remote" in text or "distributed" in text
    contract = "1099" in text or "contract" in text
    senior = any(k in text for k in SENIOR_CONSULTANT_INTENT)
    architect = any(k in text for k in ARCHITECT_INTENT)

    if remote:
        score += 15
        signals.append("Remote-friendly")
    if contract:
        score += 10
        signals.append("1099/Contract")
    if architect:
        score += 20
        role = "architect"
        signals.append("Architect-level")
    if senior and role == "consultant":
        score += 10
        role = "senior_consultant"
        signals.append("Senior Consultant Fit")

    if any(sig in text for sig in HUBSPOT_STRONG_SIGNALS):
        score += 10
        signals.append("Strong HubSpot Expertise Signal")

    return score, role, signals


def _score_generic(text: str, patterns: List[Tuple[List[str], int, str]]) -> Tuple[int, List[str]]:
    score = 0
    signals: List[str] = []
    for keywords, weight, label in patterns:
        if any(k in text for k in keywords):
            score += weight
            signals.append(label)
    return score, signals


def _score_developer(text: str) -> Tuple[int, List[str]]:
    return _score_generic(
        text,
        [
            (HUBSPOT_TECH_KEYWORDS, 25, "HubSpot mentioned"),
            (HUBSPOT_STRONG_SIGNALS, 15, "HubSpot strong signals"),
            (["cms hub"], 25, "CMS Hub"),
            (["custom module", "custom modules", "theme"], 15, "Custom modules / theme"),
            (["api", "integration", "integrations", "graphql"], 20, "HubSpot API / integrations"),
            (["developer", "engineer"], 10, "Developer title"),
        ],
    )


def _score_consultant(text: str) -> Tuple[int, List[str]]:
    return _score_generic(
        text,
        [
            (HUBSPOT_TECH_KEYWORDS, 25, "HubSpot mentioned"),
            (HUBSPOT_STRONG_SIGNALS, 15, "HubSpot strong signals"),
            (["revops", "marketing ops", "mops"], 20, "RevOps / Marketing Ops"),
            (["workflow", "automation", "implementation"], 15, "Workflow / automation"),
            (["migration", "onboarding"], 20, "CRM migration / onboarding"),
            (["consultant", "specialist", "solutions architect"], 10, "Consultant title"),
        ],
    )


def score_roles(text: str) -> Optional[SignalResult]:
    text = text.lower()

    if not ALLOW_AGENCIES and any(k in text for k in ["agency", "staffing", "recruiting"]):
        return None

    developer_score, developer_signals = _score_developer(text)
    consultant_score, consultant_signals = _score_consultant(text)

    choices: List[SignalResult] = []
    if developer_score >= 60:
        choices.append({"role": "developer", "score": developer_score, "signals": developer_signals})
    if consultant_score >= 50:
        choices.append({"role": "consultant", "score": consultant_score, "signals": consultant_signals})

    for choice in choices:
        score, role, sigs = _apply_boosters(choice["score"], choice["signals"], text, choice["role"])
        choice["score"] = score
        choice["role"] = role
        choice["signals"] = sigs

    if not choices:
        return None

    best = max(choices, key=lambda c: c["score"])

    if ROLE_FILTER and best["role"] not in ROLE_FILTER:
        return None

    if REMOTE_ONLY and not any("remote" in s.lower() for s in best["signals"]):
        return None

    return best
