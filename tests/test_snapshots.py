"""
Snapshot testing framework for extractors.

Provides:
- HTML fixtures for testing
- Expected extraction outputs
- Diffing tests for regressions
- Snapshot creation and validation
"""

import json
import logging
import unittest
from pathlib import Path
from typing import Dict, List
from difflib import unified_diff

from extractors import (
    JsonLdExtractor,
    AnchorExtractor,
    ButtonExtractor,
    SectionExtractor,
    HeadingExtractor,
    MultiLayerExtractor,
)
from enhanced_extractors import (
    MicrodataExtractor,
    OpenGraphExtractor,
    MetaTagExtractor,
    JavaScriptDataExtractor,
    CMSPatternExtractor,
)

logger = logging.getLogger(__name__)

# Directories
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


class SnapshotTester:
    """Manages snapshot testing for extractors."""

    def __init__(self, update_snapshots: bool = False):
        self.update_snapshots = update_snapshots
        self.logger = logging.getLogger(self.__class__.__name__)
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def test_extractor(
        self,
        extractor_name: str,
        html_content: str,
        extractor_class,
        base_url: str = "https://example.com"
    ) -> bool:
        """
        Test an extractor against its snapshot.

        Args:
            extractor_name: Name for snapshot file
            html_content: HTML to extract from
            extractor_class: Extractor class to test
            base_url: Base URL for extraction

        Returns:
            True if snapshot matches or was updated
        """
        # Extract jobs
        extractor = extractor_class(base_url)
        extracted = extractor.extract(html_content)

        # Normalize for comparison
        normalized = self._normalize_extraction(extracted)

        # Snapshot path
        snapshot_path = SNAPSHOTS_DIR / f"{extractor_name}.json"

        # Update mode
        if self.update_snapshots:
            self._save_snapshot(snapshot_path, normalized)
            self.logger.info("Updated snapshot: %s", snapshot_path)
            return True

        # Compare mode
        if not snapshot_path.exists():
            self.logger.warning("Snapshot missing: %s (creating)", snapshot_path)
            self._save_snapshot(snapshot_path, normalized)
            return True

        expected = self._load_snapshot(snapshot_path)
        
        if normalized == expected:
            self.logger.info("Snapshot matches: %s", extractor_name)
            return True
        else:
            self._show_diff(extractor_name, expected, normalized)
            return False

    def _normalize_extraction(self, extracted: List[Dict]) -> List[Dict]:
        """Normalize extraction results for comparison."""
        # Sort by title for consistent ordering
        normalized = sorted(extracted, key=lambda x: x.get('title', ''))
        
        # Remove unstable fields
        for job in normalized:
            job.pop('timestamp', None)
        
        return normalized

    def _save_snapshot(self, path: Path, data: List[Dict]):
        """Save snapshot to file."""
        with path.open('w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def _load_snapshot(self, path: Path) -> List[Dict]:
        """Load snapshot from file."""
        with path.open('r') as f:
            return json.load(f)

    def _show_diff(self, name: str, expected: List[Dict], actual: List[Dict]):
        """Show diff between expected and actual."""
        expected_str = json.dumps(expected, indent=2, sort_keys=True)
        actual_str = json.dumps(actual, indent=2, sort_keys=True)
        
        diff = unified_diff(
            expected_str.splitlines(keepends=True),
            actual_str.splitlines(keepends=True),
            fromfile='expected',
            tofile='actual',
        )
        
        self.logger.error("Snapshot mismatch for %s:", name)
        for line in diff:
            print(line, end='')


class TestExtractorSnapshots(unittest.TestCase):
    """Snapshot tests for all extractors."""

    @classmethod
    def setUpClass(cls):
        cls.tester = SnapshotTester(update_snapshots=False)
        cls._create_fixtures()

    @classmethod
    def _create_fixtures(cls):
        """Create HTML fixtures for testing."""
        # JSON-LD fixture
        jsonld_html = '''
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@type": "JobPosting",
            "title": "HubSpot Developer",
            "url": "https://example.com/job/123",
            "description": "We need a HubSpot CMS developer with API experience."
        }
        </script>
        </head>
        </html>
        '''
        (FIXTURES_DIR / 'jsonld_single.html').write_text(jsonld_html)

        # Microdata fixture
        microdata_html = '''
        <html>
        <body>
        <div itemscope itemtype="http://schema.org/JobPosting">
            <h2 itemprop="title">Senior Consultant</h2>
            <a itemprop="url" href="/jobs/456">Apply</a>
            <p itemprop="description">RevOps consultant with HubSpot expertise needed.</p>
            <span itemprop="jobLocation">Remote</span>
        </div>
        </body>
        </html>
        '''
        (FIXTURES_DIR / 'microdata.html').write_text(microdata_html)

        # Anchor-based fixture
        anchor_html = '''
        <html>
        <body>
        <ul>
            <li><a href="/jobs/dev">Software Developer</a></li>
            <li><a href="/jobs/eng">Platform Engineer</a></li>
            <li><a href="/about">About Us</a></li>
        </ul>
        </body>
        </html>
        '''
        (FIXTURES_DIR / 'anchors.html').write_text(anchor_html)

        # Section-based fixture
        section_html = '''
        <html>
        <body>
        <h2>Open Positions</h2>
        <div class="job-card">
            <h3>Marketing Consultant</h3>
            <a href="/apply/1">Apply Now</a>
            <p class="description">HubSpot marketing automation expert needed.</p>
        </div>
        <div class="job-card">
            <h3>Sales Operations Manager</h3>
            <a href="/apply/2">Learn More</a>
        </div>
        </body>
        </html>
        '''
        (FIXTURES_DIR / 'sections.html').write_text(section_html)

        # JavaScript data fixture
        js_html = '''
        <html>
        <head>
        <script id="__NEXT_DATA__" type="application/json">
        {
            "props": {
                "pageProps": {
                    "jobs": [
                        {
                            "title": "DevOps Engineer",
                            "url": "/careers/devops",
                            "description": "Manage our cloud infrastructure"
                        }
                    ]
                }
            }
        }
        </script>
        </head>
        </html>
        '''
        (FIXTURES_DIR / 'javascript.html').write_text(js_html)

    def test_jsonld_extractor(self):
        """Test JSON-LD extractor."""
        html = (FIXTURES_DIR / 'jsonld_single.html').read_text()
        result = self.tester.test_extractor(
            'jsonld_single',
            html,
            JsonLdExtractor
        )
        self.assertTrue(result, "JSON-LD snapshot mismatch")

    def test_microdata_extractor(self):
        """Test microdata extractor."""
        html = (FIXTURES_DIR / 'microdata.html').read_text()
        result = self.tester.test_extractor(
            'microdata',
            html,
            MicrodataExtractor
        )
        self.assertTrue(result, "Microdata snapshot mismatch")

    def test_anchor_extractor(self):
        """Test anchor extractor."""
        html = (FIXTURES_DIR / 'anchors.html').read_text()
        result = self.tester.test_extractor(
            'anchors',
            html,
            AnchorExtractor
        )
        self.assertTrue(result, "Anchor snapshot mismatch")

    def test_section_extractor(self):
        """Test section extractor."""
        html = (FIXTURES_DIR / 'sections.html').read_text()
        result = self.tester.test_extractor(
            'sections',
            html,
            SectionExtractor
        )
        self.assertTrue(result, "Section snapshot mismatch")

    def test_javascript_extractor(self):
        """Test JavaScript data extractor."""
        html = (FIXTURES_DIR / 'javascript.html').read_text()
        result = self.tester.test_extractor(
            'javascript',
            html,
            JavaScriptDataExtractor
        )
        self.assertTrue(result, "JavaScript snapshot mismatch")

    def test_multi_layer_extractor(self):
        """Test multi-layer extractor with combined HTML."""
        # Combine multiple fixtures
        combined_html = (
            (FIXTURES_DIR / 'jsonld_single.html').read_text() +
            (FIXTURES_DIR / 'anchors.html').read_text()
        )
        
        # Special handling for MultiLayerExtractor
        extractor = MultiLayerExtractor("https://example.com")
        extracted = extractor.extract_all(combined_html)
        
        # Normalize for comparison
        normalized = self.tester._normalize_extraction(extracted)
        
        # Snapshot path
        snapshot_path = SNAPSHOTS_DIR / "multi_layer.json"
        
        if not snapshot_path.exists():
            self.tester._save_snapshot(snapshot_path, normalized)
            self.assertTrue(True, "Snapshot created")
        else:
            expected = self.tester._load_snapshot(snapshot_path)
            self.assertEqual(normalized, expected, "Multi-layer snapshot mismatch")


class TestRegressionDetection(unittest.TestCase):
    """Tests for detecting regressions in extraction."""

    def test_no_duplicate_extraction(self):
        """Ensure extractors don't produce duplicates."""
        html = '''
        <html>
        <body>
            <a href="/job/1">Developer Position</a>
            <a href="/job/1">Developer Position</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should deduplicate
        titles = [j['title'] for j in jobs]
        self.assertEqual(len(titles), len(set(titles)), "Duplicates not filtered")

    def test_url_normalization(self):
        """Ensure URLs are properly normalized."""
        html = '''
        <html>
        <body>
            <a href="../jobs/dev">Developer</a>
            <a href="/jobs/eng">Engineer</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com/careers/")
        jobs = extractor.extract(html)
        
        for job in jobs:
            if job.get('url'):
                self.assertTrue(job['url'].startswith('http'), f"URL not normalized: {job['url']}")

    def test_html_cleanup(self):
        """Ensure HTML tags are cleaned from text."""
        html = '''
        <html>
        <body>
            <a href="/job/1"><strong>Senior</strong> Developer</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        if jobs:
            title = jobs[0]['title']
            self.assertNotIn('<', title, "HTML tags not cleaned")
            self.assertNotIn('>', title, "HTML tags not cleaned")


if __name__ == "__main__":
    # Run with: python -m unittest test_snapshots -v
    # Update snapshots with: UPDATE_SNAPSHOTS=1 python test_snapshots.py
    unittest.main()
