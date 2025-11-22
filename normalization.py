"""
Normalization utilities for job data.

Provides comprehensive normalization for:
- Job titles
- Locations
- Employment types
- Compensation
- Remote/onsite labels
- Summaries
- HTML cleanup
"""

import re
import logging
from typing import Dict, Optional, Set
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Title normalization mappings
TITLE_SYNONYMS = {
    # Engineering titles
    "software developer": "software engineer",
    "programmer": "software engineer",
    "coder": "software engineer",
    "dev": "developer",
    "swe": "software engineer",
    "sde": "software engineer",
    
    # Leadership titles
    "head of": "director",
    "vp": "vice president",
    "evp": "executive vice president",
    "svp": "senior vice president",
    "cto": "chief technology officer",
    "ceo": "chief executive officer",
    "cmo": "chief marketing officer",
    
    # RevOps/Operations
    "revops": "revenue operations",
    "mops": "marketing operations",
    "salesops": "sales operations",
    
    # Consultant variations
    "implementation specialist": "implementation consultant",
    "solutions engineer": "solutions consultant",
    
    # Common abbreviations
    "sr": "senior",
    "sr.": "senior",
    "jr": "junior",
    "jr.": "junior",
}

# Department classification
DEPARTMENTS = {
    "engineering": ["engineer", "developer", "programmer", "architect", "devops", "sre", "qa", "test"],
    "marketing": ["marketing", "growth", "demand gen", "content", "seo", "sem", "brand"],
    "sales": ["sales", "account executive", "ae", "bdr", "sdr", "account manager"],
    "operations": ["operations", "ops", "revops", "salesops", "mops", "bizops"],
    "customer_success": ["customer success", "cs", "support", "technical support"],
    "product": ["product manager", "pm", "product owner", "product designer"],
    "hubspot": ["hubspot", "crm consultant", "hubspot specialist"],
}

# Location normalization
LOCATION_PATTERNS = {
    "remote": re.compile(r'\b(remote|work from home|wfh|anywhere|distributed)\b', re.IGNORECASE),
    "hybrid": re.compile(r'\b(hybrid|flexible|office optional)\b', re.IGNORECASE),
    "onsite": re.compile(r'\b(on-site|onsite|in-office|office-based)\b', re.IGNORECASE),
}

# Employment type patterns
EMPLOYMENT_TYPE_PATTERNS = {
    "full_time": re.compile(r'\b(full[- ]time|ft|permanent)\b', re.IGNORECASE),
    "part_time": re.compile(r'\b(part[- ]time|pt)\b', re.IGNORECASE),
    "contract": re.compile(r'\b(contract|contractor|1099|freelance|temp)\b', re.IGNORECASE),
    "intern": re.compile(r'\b(intern|internship|co-op)\b', re.IGNORECASE),
}

# Seniority levels
SENIORITY_PATTERNS = {
    "entry": re.compile(r'\b(entry[- ]level|junior|jr|associate|i\b)', re.IGNORECASE),
    "mid": re.compile(r'\b(mid[- ]level|ii\b|2\b)', re.IGNORECASE),
    "senior": re.compile(r'\b(senior|sr|lead|iii\b|3\b)', re.IGNORECASE),
    "staff": re.compile(r'\b(staff|principal|iv\b|4\b)', re.IGNORECASE),
    "director": re.compile(r'\b(director|head of|vp|vice president)\b', re.IGNORECASE),
    "executive": re.compile(r'\b(c-level|cto|ceo|cmo|coo|cfo)\b', re.IGNORECASE),
}


class JobNormalizer:
    """Normalizes job data fields."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def normalize_title(self, title: str) -> str:
        """
        Normalize job title.

        Args:
            title: Raw job title

        Returns:
            Normalized title
        """
        if not title:
            return ""

        # Clean HTML
        title = self._strip_html(title)
        
        # Convert to lowercase for processing
        title_lower = title.lower().strip()
        
        # Apply synonym mappings
        for synonym, canonical in TITLE_SYNONYMS.items():
            title_lower = re.sub(r'\b' + re.escape(synonym) + r'\b', canonical, title_lower)
        
        # Clean up whitespace
        title_lower = re.sub(r'\s+', ' ', title_lower).strip()
        
        # Title case
        title_normalized = ' '.join(word.capitalize() for word in title_lower.split())
        
        return title_normalized

    def normalize_location(self, location: str) -> Dict[str, str]:
        """
        Normalize location string.

        Args:
            location: Raw location string

        Returns:
            Dict with normalized location data
        """
        if not location:
            return {"raw": "", "type": "unknown", "city": "", "state": "", "country": ""}

        location = self._strip_html(location).strip()
        
        # Detect location type
        location_type = "onsite"  # default
        for loc_type, pattern in LOCATION_PATTERNS.items():
            if pattern.search(location):
                location_type = loc_type
                break

        # Parse city, state, country (basic parsing)
        parts = [p.strip() for p in location.split(',')]
        city = parts[0] if len(parts) > 0 else ""
        state = parts[1] if len(parts) > 1 else ""
        country = parts[-1] if len(parts) > 2 else ""

        return {
            "raw": location,
            "type": location_type,
            "city": city,
            "state": state,
            "country": country,
        }

    def normalize_employment_type(self, text: str) -> str:
        """
        Detect and normalize employment type.

        Args:
            text: Text to analyze

        Returns:
            Employment type (full_time, part_time, contract, intern, unknown)
        """
        if not text:
            return "unknown"

        for emp_type, pattern in EMPLOYMENT_TYPE_PATTERNS.items():
            if pattern.search(text):
                return emp_type

        return "full_time"  # default assumption

    def normalize_seniority(self, title: str) -> str:
        """
        Detect seniority level from title.

        Args:
            title: Job title

        Returns:
            Seniority level
        """
        if not title:
            return "mid"  # default

        for level, pattern in SENIORITY_PATTERNS.items():
            if pattern.search(title):
                return level

        return "mid"

    def classify_department(self, title: str, description: str = "") -> str:
        """
        Classify job into department.

        Args:
            title: Job title
            description: Job description (optional)

        Returns:
            Department name
        """
        text = f"{title} {description}".lower()

        # Check each department
        for dept, keywords in DEPARTMENTS.items():
            if any(keyword in text for keyword in keywords):
                return dept

        return "other"

    def normalize_compensation(self, text: str) -> Optional[Dict]:
        """
        Extract and normalize compensation information.

        Args:
            text: Text containing compensation info

        Returns:
            Dict with compensation data or None
        """
        if not text:
            return None

        # Extract salary ranges
        # Patterns: $100,000 - $150,000, 100k-150k, $100K - $150K
        pattern = r'\$?([\d,]+)k?\s*[-–to]\s*\$?([\d,]+)k?'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            try:
                min_val = int(match.group(1).replace(',', ''))
                max_val = int(match.group(2).replace(',', ''))
                
                # Normalize k notation
                if 'k' in text.lower() and min_val < 1000:
                    min_val *= 1000
                if 'k' in text.lower() and max_val < 1000:
                    max_val *= 1000
                
                return {
                    "min": min_val,
                    "max": max_val,
                    "currency": "USD",
                    "period": "annual",
                }
            except ValueError:
                pass

        return None

    def normalize_summary(self, summary: str, max_length: int = 500) -> str:
        """
        Normalize and truncate summary text.

        Args:
            summary: Raw summary text
            max_length: Maximum length

        Returns:
            Normalized summary
        """
        if not summary:
            return ""

        # Strip HTML
        summary = self._strip_html(summary)
        
        # Clean whitespace
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        # Truncate
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."

        return summary

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        soup = BeautifulSoup(text, 'lxml')
        return soup.get_text(separator=' ', strip=True)


class TitleClassifier:
    """Advanced title classification using keyword clustering."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.normalizer = JobNormalizer()

    def classify_title(self, title: str) -> Dict:
        """
        Classify a job title comprehensively.

        Args:
            title: Job title

        Returns:
            Dict with classification details
        """
        normalized = self.normalizer.normalize_title(title)
        
        return {
            "original": title,
            "normalized": normalized,
            "department": self.normalizer.classify_department(title),
            "seniority": self.normalizer.normalize_seniority(title),
            "is_technical": self._is_technical(title),
            "is_leadership": self._is_leadership(title),
            "is_hubspot_focused": self._is_hubspot_focused(title),
        }

    def _is_technical(self, title: str) -> bool:
        """Check if title is technical."""
        technical_keywords = ["engineer", "developer", "architect", "devops", "qa", "sre", "programmer"]
        return any(keyword in title.lower() for keyword in technical_keywords)

    def _is_leadership(self, title: str) -> bool:
        """Check if title is leadership."""
        leadership_keywords = ["director", "vp", "head of", "chief", "cto", "ceo", "lead", "principal"]
        return any(keyword in title.lower() for keyword in leadership_keywords)

    def _is_hubspot_focused(self, title: str) -> bool:
        """Check if title is HubSpot-focused."""
        hubspot_keywords = ["hubspot", "crm", "revops", "marketing ops"]
        return any(keyword in title.lower() for keyword in hubspot_keywords)
