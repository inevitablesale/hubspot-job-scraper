"""
Role scoring and classification engine for HubSpot job scraper.

Classifies jobs as developer, consultant, architect, or senior consultant
based on content analysis and keyword matching.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# HubSpot technology keywords
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
    "dashboards",
    "portal",
    "map properties",
    "api",
    "app",
    "private app token",
]

# Strong HubSpot expertise signals
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

# Developer role intent keywords
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
    "developer",
    "engineer",
    "software engineer",
    "full stack",
    "frontend",
    "backend",
]

# Consultant role intent keywords
CONSULTANT_INTENT = [
    "hubspot consultant",
    "crm consultant",
    "revops consultant",
    "marketing ops",
    "solutions architect",
    "hubspot onboarding",
    "hubspot implementation",
    "hubspot specialist",
    "revops specialist",
    "workflow automation",
    "consultant",
    "specialist",
]

# Senior consultant keywords
SENIOR_CONSULTANT_INTENT = [
    "senior consultant",
    "lead consultant",
    "principal consultant",
    "senior specialist",
    "lead specialist",
]

# Architect role keywords
ARCHITECT_INTENT = [
    "solutions architect",
    "revops architect",
    "technical architect",
    "systems architect",
    "enterprise architect",
    "architect",
]

# Remote/location keywords
REMOTE_KEYWORDS = [
    "remote",
    "distributed",
    "work from home",
    "wfh",
    "anywhere",
    "flexible location",
]

# Hybrid keywords
HYBRID_KEYWORDS = [
    "hybrid",
    "flexible",
    "remote-friendly",
    "office optional",
]

# Contract/1099 keywords
CONTRACT_KEYWORDS = [
    "1099",
    "contract",
    "contractor",
    "freelance",
    "independent contractor",
]

# Agency/staffing indicators (to filter out)
AGENCY_KEYWORDS = [
    "staffing agency",
    "recruiting agency",
    "placement agency",
    "talent agency",
]


class RoleClassifier:
    """Classifies and scores job roles based on content analysis."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def classify_and_score(self, content: str, job_data: Dict) -> Optional[Dict]:
        """
        Classify a job and calculate its score.

        Args:
            content: Full text content to analyze (HTML converted to text)
            job_data: Job data dict with title, url, summary

        Returns:
            Dict with role, score, signals, and location info, or None if below threshold
        """
        content_lower = content.lower()

        # Check if it's an agency page (filter out unless explicitly allowed)
        if self._is_agency_page(content_lower):
            self.logger.debug("Filtering out agency/staffing page")
            return None

        # Score as developer and consultant
        developer_score, developer_signals = self._score_developer(content_lower)
        consultant_score, consultant_signals = self._score_consultant(content_lower)

        # Detect subtypes
        is_senior = any(k in content_lower for k in SENIOR_CONSULTANT_INTENT)
        is_architect = any(k in content_lower for k in ARCHITECT_INTENT)
        is_remote = any(k in content_lower for k in REMOTE_KEYWORDS)
        is_hybrid = any(k in content_lower for k in HYBRID_KEYWORDS)
        is_contract = any(k in content_lower for k in CONTRACT_KEYWORDS)

        # Build candidate roles
        candidates = []
        if developer_score >= 60:
            candidates.append({
                "role": "developer",
                "score": developer_score,
                "signals": developer_signals.copy(),
            })

        if consultant_score >= 50:
            candidates.append({
                "role": "consultant",
                "score": consultant_score,
                "signals": consultant_signals.copy(),
            })

        # Apply boosters and modifiers
        for candidate in candidates:
            if is_remote:
                candidate["score"] += 15
                candidate["signals"].append("Remote-friendly")
            if is_hybrid:
                candidate["score"] += 10
                candidate["signals"].append("Hybrid work")
            if is_contract:
                candidate["score"] += 10
                candidate["signals"].append("1099/Contract")
            if is_architect:
                candidate["score"] += 20
                candidate["role"] = "architect"
                candidate["signals"].append("Architect-level")
            if is_senior and candidate["role"] == "consultant":
                candidate["score"] += 10
                candidate["role"] = "senior_consultant"
                candidate["signals"].append("Senior Consultant Fit")

            # Boost for strong HubSpot signals
            if any(sig in content_lower for sig in HUBSPOT_STRONG_SIGNALS):
                candidate["score"] += 10
                candidate["signals"].append("Strong HubSpot Expertise Signal")

        if not candidates:
            return None

        # Return the highest scoring role
        best_match = max(candidates, key=lambda c: c["score"])

        # Detect location type
        location_type = "onsite"
        if is_remote:
            location_type = "remote"
        elif is_hybrid:
            location_type = "hybrid"

        return {
            "role": best_match["role"],
            "score": best_match["score"],
            "signals": best_match["signals"],
            "location_type": location_type,
            "is_contract": is_contract,
        }

    def _score_developer(self, content: str) -> Tuple[int, List[str]]:
        """Score content as a developer role."""
        # Must have both tech keywords and developer intent
        if not self._has_tech_and_intent(content, DEVELOPER_INTENT):
            return 0, []

        rules = [
            (HUBSPOT_TECH_KEYWORDS, 25, "HubSpot mentioned"),
            (HUBSPOT_STRONG_SIGNALS, 15, "HubSpot strong signals"),
            (["cms hub"], 25, "CMS Hub"),
            (["custom module", "custom modules", "theme development", "hubspot theme"], 15, "Theme/modules"),
            (["hubspot api", "api", "integrations", "private app"], 20, "HubSpot API/Integrations"),
            (["developer", "engineer", "software engineer"], 10, "Developer title"),
            (["react", "vue", "angular", "javascript", "typescript"], 5, "Modern JS frameworks"),
            (["python", "node", "nodejs"], 5, "Backend languages"),
        ]

        return self._apply_scoring_rules(content, rules)

    def _score_consultant(self, content: str) -> Tuple[int, List[str]]:
        """Score content as a consultant role."""
        # Must have both tech keywords and consultant intent
        if not self._has_tech_and_intent(content, CONSULTANT_INTENT):
            return 0, []

        rules = [
            (HUBSPOT_TECH_KEYWORDS, 25, "HubSpot mentioned"),
            (HUBSPOT_STRONG_SIGNALS, 15, "HubSpot strong signals"),
            (["revops", "marketing ops", "mops", "revenue operations"], 20, "RevOps/Marketing Ops"),
            (["workflows", "automation", "implementation"], 15, "Automation/Implementation"),
            (["crm migration", "onboarding", "data migration"], 20, "CRM migration/onboarding"),
            (["consultant", "specialist", "solutions architect"], 10, "Consultant title"),
            (["sales", "marketing", "service"], 5, "Business functions"),
        ]

        return self._apply_scoring_rules(content, rules)

    def _has_tech_and_intent(self, content: str, intent_keywords: List[str]) -> bool:
        """Check if content has both HubSpot tech keywords and role intent."""
        has_tech = any(k in content for k in HUBSPOT_TECH_KEYWORDS)
        has_intent = any(k in content for k in intent_keywords)
        return has_tech and has_intent

    def _apply_scoring_rules(self, content: str, rules: List[Tuple]) -> Tuple[int, List[str]]:
        """Apply scoring rules and return score + signals."""
        score = 0
        signals = []

        for keywords, points, label in rules:
            if any(kw in content for kw in keywords):
                score += points
                signals.append(label)

        return score, signals

    def _is_agency_page(self, content: str) -> bool:
        """Check if this is an agency/staffing page (to filter out)."""
        if os.getenv("ALLOW_AGENCIES", "false").lower() == "true":
            return False

        return any(keyword in content for keyword in AGENCY_KEYWORDS)

    def should_include_role(self, role: str, location_type: str) -> bool:
        """
        Check if a role should be included based on filters.

        Args:
            role: The classified role
            location_type: The location type (remote/hybrid/onsite)

        Returns:
            True if the role passes filters
        """
        # Role filter
        role_filter = os.getenv("ROLE_FILTER", "")
        if role_filter:
            allowed_roles = {r.strip() for r in role_filter.split(",") if r.strip()}
            if role not in allowed_roles:
                self.logger.debug("Role %s filtered out by ROLE_FILTER", role)
                return False

        # Remote-only filter
        remote_only = os.getenv("REMOTE_ONLY", "false").lower() == "true"
        if remote_only and location_type != "remote":
            self.logger.debug("Non-remote role filtered out by REMOTE_ONLY")
            return False

        return True
