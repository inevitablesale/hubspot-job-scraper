"""
Advanced deduplication and job tracking.

Provides:
- Cross-layer deduplication with fuzzy matching
- Incremental crawl tracking
- Job change detection
- Company health signal generation
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class JobDeduplicator:
    """Advanced deduplication with fuzzy matching."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.seen_hashes: Set[str] = set()
        self.seen_jobs: List[Dict] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_job_hash(self, job: Dict) -> str:
        """
        Generate hash for job.

        Uses: title, location, url, summary
        """
        components = [
            job.get('title', '').lower().strip(),
            job.get('location', '').lower().strip(),
            job.get('url', '').lower().strip(),
            job.get('summary', '')[:100].lower().strip(),
        ]
        
        hash_string = '|'.join(components)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def is_duplicate(self, job: Dict, use_fuzzy: bool = True) -> bool:
        """
        Check if job is duplicate.

        Args:
            job: Job dict to check
            use_fuzzy: Whether to use fuzzy matching when URLs differ

        Returns:
            True if duplicate
        """
        # Exact hash match
        job_hash = self.get_job_hash(job)
        if job_hash in self.seen_hashes:
            return True

        # Fuzzy matching if enabled
        if use_fuzzy:
            for seen_job in self.seen_jobs:
                if self._is_fuzzy_match(job, seen_job):
                    self.logger.debug("Fuzzy match: %s ~ %s", job.get('title'), seen_job.get('title'))
                    return True

        # Not a duplicate - add to seen
        self.seen_hashes.add(job_hash)
        self.seen_jobs.append(job)
        return False

    def _is_fuzzy_match(self, job1: Dict, job2: Dict) -> bool:
        """
        Check if two jobs are fuzzy matches.

        Considers:
        - Title similarity
        - Location similarity
        - URL match (if both present)
        """
        # If URLs match exactly, it's the same job
        url1 = job1.get('url', '')
        url2 = job2.get('url', '')
        if url1 and url2 and url1 == url2:
            return True

        # Check title similarity
        title1 = job1.get('title', '').lower()
        title2 = job2.get('title', '').lower()
        title_similarity = SequenceMatcher(None, title1, title2).ratio()

        if title_similarity < self.similarity_threshold:
            return False

        # Check location similarity if present
        loc1 = job1.get('location', '').lower()
        loc2 = job2.get('location', '').lower()
        
        if loc1 and loc2:
            loc_similarity = SequenceMatcher(None, loc1, loc2).ratio()
            return loc_similarity >= self.similarity_threshold

        # If only title similarity is high enough
        return title_similarity >= 0.95  # Higher threshold when location missing

    def clear(self):
        """Clear seen jobs."""
        self.seen_hashes.clear()
        self.seen_jobs.clear()


class IncrementalTracker:
    """Tracks job changes over time for incremental crawling."""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.previous_jobs: Dict[str, Dict] = {}
        self.current_jobs: Dict[str, Dict] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._load_cache()

    def _load_cache(self):
        """Load previous job state."""
        if self.cache_file.exists():
            try:
                with self.cache_file.open('r') as f:
                    data = json.load(f)
                    self.previous_jobs = data.get('jobs', {})
                    self.logger.info("Loaded %d previous jobs", len(self.previous_jobs))
            except Exception as e:
                self.logger.warning("Failed to load cache: %s", e)

    def save_cache(self):
        """Save current job state."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_file.open('w') as f:
                json.dump({
                    'jobs': self.current_jobs,
                    'updated_at': datetime.utcnow().isoformat(),
                }, f, indent=2)
            self.logger.info("Saved %d jobs to cache", len(self.current_jobs))
        except Exception as e:
            self.logger.error("Failed to save cache: %s", e)

    def add_job(self, company: str, job: Dict):
        """Add current job."""
        key = f"{company}:{job.get('url', job.get('title'))}"
        self.current_jobs[key] = {
            'company': company,
            'job': job,
            'seen_at': datetime.utcnow().isoformat(),
        }

    def get_changes(self, company: str) -> Dict[str, List[Dict]]:
        """
        Get job changes for a company.

        Returns:
            Dict with 'new', 'removed', 'updated' lists
        """
        changes = {
            'new': [],
            'removed': [],
            'updated': [],
        }

        # Find previous jobs for this company
        prev_company_jobs = {
            k: v for k, v in self.previous_jobs.items()
            if v.get('company') == company
        }

        # Find current jobs for this company
        curr_company_jobs = {
            k: v for k, v in self.current_jobs.items()
            if v.get('company') == company
        }

        # New jobs
        for key, data in curr_company_jobs.items():
            if key not in prev_company_jobs:
                changes['new'].append(data['job'])

        # Removed jobs
        for key, data in prev_company_jobs.items():
            if key not in curr_company_jobs:
                changes['removed'].append(data['job'])

        # Updated jobs (same key, different content)
        for key in set(prev_company_jobs.keys()) & set(curr_company_jobs.keys()):
            prev_job = prev_company_jobs[key]['job']
            curr_job = curr_company_jobs[key]['job']
            
            if prev_job != curr_job:
                changes['updated'].append(curr_job)

        return changes


class CompanyHealthAnalyzer:
    """Generates company health signals from hiring trends."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_hiring_trend(self, changes: Dict[str, List[Dict]]) -> Dict:
        """
        Analyze hiring trends and generate health signals.

        Args:
            changes: Dict with 'new', 'removed', 'updated' job lists

        Returns:
            Health analysis dict
        """
        new_count = len(changes['new'])
        removed_count = len(changes['removed'])
        updated_count = len(changes['updated'])

        # Calculate net change
        net_change = new_count - removed_count

        # Determine trend
        if net_change > 5:
            trend = "expanding"
            reason = "Significant increase in job postings"
        elif net_change < -5:
            trend = "contracting"
            reason = "Significant decrease in job postings"
        elif new_count > 10:
            trend = "actively_hiring"
            reason = "High volume of new positions"
        else:
            trend = "stable"
            reason = "Steady hiring activity"

        # Analyze role types in new jobs
        role_analysis = self._analyze_roles(changes['new'])

        # Generate insights
        insights = []
        
        if role_analysis.get('engineering', 0) > 5:
            insights.append("Surge in engineering roles")
        
        if role_analysis.get('leadership', 0) > 0:
            insights.append("Hiring for leadership positions")
        
        if removed_count > 0 and 'leadership' in self._get_removed_roles(changes['removed']):
            insights.append("Disappearance of leadership roles")

        if new_count > 0:
            avg_seniority = self._calculate_avg_seniority(changes['new'])
            if avg_seniority == "entry":
                insights.append("Focus on entry-level hires")
            elif avg_seniority == "senior":
                insights.append("Focus on senior talent")

        return {
            'trend': trend,
            'reason': reason,
            'net_change': net_change,
            'new_jobs': new_count,
            'removed_jobs': removed_count,
            'updated_jobs': updated_count,
            'insights': insights,
            'role_breakdown': role_analysis,
        }

    def _analyze_roles(self, jobs: List[Dict]) -> Dict[str, int]:
        """Analyze role types in job list."""
        roles = {
            'engineering': 0,
            'sales': 0,
            'marketing': 0,
            'operations': 0,
            'leadership': 0,
            'customer_success': 0,
        }

        for job in jobs:
            title = job.get('title', '').lower()
            
            if any(keyword in title for keyword in ['engineer', 'developer', 'architect']):
                roles['engineering'] += 1
            
            if any(keyword in title for keyword in ['director', 'vp', 'head of', 'chief']):
                roles['leadership'] += 1
            
            if any(keyword in title for keyword in ['sales', 'account executive']):
                roles['sales'] += 1
            
            if any(keyword in title for keyword in ['marketing', 'growth']):
                roles['marketing'] += 1
            
            if any(keyword in title for keyword in ['operations', 'ops']):
                roles['operations'] += 1
            
            if any(keyword in title for keyword in ['customer success', 'support']):
                roles['customer_success'] += 1

        return roles

    def _get_removed_roles(self, jobs: List[Dict]) -> Set[str]:
        """Get role types from removed jobs."""
        roles = set()
        for job in jobs:
            title = job.get('title', '').lower()
            if any(keyword in title for keyword in ['director', 'vp', 'head of', 'chief']):
                roles.add('leadership')
        return roles

    def _calculate_avg_seniority(self, jobs: List[Dict]) -> str:
        """Calculate average seniority level."""
        seniority_scores = {
            'entry': 0,
            'mid': 0,
            'senior': 0,
            'leadership': 0,
        }

        for job in jobs:
            title = job.get('title', '').lower()
            
            if any(keyword in title for keyword in ['junior', 'entry', 'associate']):
                seniority_scores['entry'] += 1
            elif any(keyword in title for keyword in ['senior', 'lead', 'staff', 'principal']):
                seniority_scores['senior'] += 1
            elif any(keyword in title for keyword in ['director', 'vp', 'head', 'chief']):
                seniority_scores['leadership'] += 1
            else:
                seniority_scores['mid'] += 1

        # Return most common
        return max(seniority_scores, key=seniority_scores.get)
