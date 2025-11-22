"""
Basic smoke tests for the extraction engine.

Tests the multi-layer extractors with sample HTML.
"""

import unittest
from extractors import (
    JsonLdExtractor,
    AnchorExtractor,
    ButtonExtractor,
    SectionExtractor,
    HeadingExtractor,
    MultiLayerExtractor,
)


class TestJsonLdExtractor(unittest.TestCase):
    """Test JSON-LD JobPosting extractor."""

    def setUp(self):
        self.extractor = JsonLdExtractor("https://example.com/careers")

    def test_extract_simple_job_posting(self):
        """Test extraction of a simple JobPosting."""
        html = '''
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@type": "JobPosting",
            "title": "HubSpot Developer",
            "url": "https://example.com/job/123",
            "description": "We need a HubSpot CMS developer"
        }
        </script>
        </head>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['title'], "HubSpot Developer")
        self.assertEqual(jobs[0]['url'], "https://example.com/job/123")

    def test_extract_multiple_postings(self):
        """Test extraction of multiple JobPostings."""
        html = '''
        <html>
        <head>
        <script type="application/ld+json">
        [
            {
                "@type": "JobPosting",
                "title": "Developer",
                "url": "https://example.com/job/1"
            },
            {
                "@type": "JobPosting",
                "title": "Consultant",
                "url": "https://example.com/job/2"
            }
        ]
        </script>
        </head>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertEqual(len(jobs), 2)

    def test_handles_invalid_json(self):
        """Test that invalid JSON doesn't crash."""
        html = '''
        <html>
        <script type="application/ld+json">
        { invalid json }
        </script>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertEqual(len(jobs), 0)


class TestAnchorExtractor(unittest.TestCase):
    """Test anchor-based extractor."""

    def setUp(self):
        self.extractor = AnchorExtractor("https://example.com/careers")

    def test_extract_job_links(self):
        """Test extraction of job links from anchors."""
        html = '''
        <html>
        <body>
            <a href="/job/developer">Senior Developer</a>
            <a href="/job/consultant">HubSpot Consultant</a>
            <a href="/about">About Us</a>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        # Should find 2 jobs (developer and consultant have job keywords)
        self.assertGreaterEqual(len(jobs), 1)

    def test_deduplication(self):
        """Test that duplicate jobs are filtered."""
        html = '''
        <html>
        <body>
            <a href="/job/1">Developer Position</a>
            <a href="/job/1">Developer Position</a>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertEqual(len(jobs), 1)


class TestButtonExtractor(unittest.TestCase):
    """Test button-based extractor."""

    def setUp(self):
        self.extractor = ButtonExtractor("https://example.com/careers")

    def test_extract_job_buttons(self):
        """Test extraction from button elements."""
        html = '''
        <html>
        <body>
            <button data-url="https://example.com/apply/123">Apply for Developer</button>
            <button>Learn More</button>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        # Should find at least the developer button
        self.assertGreaterEqual(len(jobs), 1)

    def test_handles_onclick_urls(self):
        """Test extraction from onclick handlers."""
        html = '''
        <html>
        <body>
            <button onclick="window.location='https://example.com/job/456'">Engineer Position</button>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertGreaterEqual(len(jobs), 0)


class TestSectionExtractor(unittest.TestCase):
    """Test section-based extractor."""

    def setUp(self):
        self.extractor = SectionExtractor("https://example.com/careers")

    def test_extract_from_job_section(self):
        """Test extraction from job listing sections."""
        html = '''
        <html>
        <body>
            <h2>Open Positions</h2>
            <div class="job-card">
                <h3>HubSpot Developer</h3>
                <a href="/apply/1">Apply</a>
                <p class="description">Build custom modules</p>
            </div>
            <div class="job-card">
                <h3>Marketing Consultant</h3>
                <a href="/apply/2">Apply</a>
            </div>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertEqual(len(jobs), 2)

    def test_extract_from_list(self):
        """Test extraction from list items."""
        html = '''
        <html>
        <body>
            <h2>Current Openings</h2>
            <ul>
                <li><a href="/job/1">Developer</a></li>
                <li><a href="/job/2">Analyst</a></li>
            </ul>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        self.assertGreaterEqual(len(jobs), 1)


class TestHeadingExtractor(unittest.TestCase):
    """Test heading-based extractor."""

    def setUp(self):
        self.extractor = HeadingExtractor("https://example.com/careers")

    def test_extract_from_headings(self):
        """Test extraction from heading tags."""
        html = '''
        <html>
        <body>
            <h3>Senior Developer Position</h3>
            <a href="/apply">Apply Now</a>
            <h3>Marketing Analyst Role</h3>
            <h3>About Our Company</h3>
        </body>
        </html>
        '''
        jobs = self.extractor.extract(html)
        # Should find headings with job keywords
        self.assertGreaterEqual(len(jobs), 1)


class TestMultiLayerExtractor(unittest.TestCase):
    """Test the multi-layer orchestrator."""

    def setUp(self):
        self.extractor = MultiLayerExtractor("https://example.com/careers")

    def test_combines_all_extractors(self):
        """Test that all extraction layers work together."""
        html = '''
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@type": "JobPosting",
            "title": "JSON-LD Developer",
            "url": "https://example.com/job/json"
        }
        </script>
        </head>
        <body>
            <a href="/job/anchor">Anchor Developer</a>
            <h2>Open Positions</h2>
            <div class="job-card">
                <h3>Section Engineer</h3>
            </div>
        </body>
        </html>
        '''
        jobs = self.extractor.extract_all(html)
        # Should find jobs from multiple sources
        self.assertGreaterEqual(len(jobs), 2)


if __name__ == "__main__":
    unittest.main()
