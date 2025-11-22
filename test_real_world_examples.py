"""
Test with real-world examples from production logs.

These are actual false positives that were being extracted.
"""

import unittest
from extractors import MultiLayerExtractor


class TestRealWorldExamples(unittest.TestCase):
    """Test with real examples from production logs."""

    def test_hyphadev_false_positives(self):
        """Test false positives from hyphadev.io/careers."""
        html = '''
        <html>
        <body>
            <a href="/blog/inbound-marketing">Inbound Marketing & Strategic Content</a>
            <a href="/blog/what-is-inbound">What Is Inbound Marketing?</a>
            <a href="/blog/content-marketing">What Is Content Marketing?</a>
            <a href="/apply">Apply Today</a>
        </body>
        </html>
        '''
        
        extractor = MultiLayerExtractor("https://www.hyphadev.io/careers")
        jobs = extractor.extract_all(html)
        
        # These should NOT be extracted
        titles = [job['title'].lower() for job in jobs]
        
        self.assertFalse(any('what is' in t for t in titles), 
                        "Question-format articles should not be extracted")
        self.assertFalse(any(t == 'apply today' for t in titles),
                        "Generic CTAs should not be extracted")
        self.assertFalse(any('inbound marketing & strategic content' in t for t in titles),
                        "Blog post titles should not be extracted")

    def test_clearpivot_false_positives(self):
        """Test false positives from clearpivot.com."""
        html = '''
        <html>
        <body>
            <a href="/podcast/episode-57">Episode 57: Why The Smartest Marketing Teams Still Bet Big On In-person Events</a>
            <a href="https://youtube.com/watch">Watch On Youtube</a>
            <a href="https://podcasts.apple.com">Apple Podcasts Listen On Apple Podcasts</a>
            <a href="https://spotify.com">Spotify Listen On Spotify</a>
            <a href="/jobs/solutions-architect">Solutions Architect</a>
        </body>
        </html>
        '''
        
        extractor = MultiLayerExtractor("https://www.clearpivot.com")
        jobs = extractor.extract_all(html)
        
        # Should only extract Solutions Architect
        self.assertGreater(len(jobs), 0, "Should extract Solutions Architect")
        
        titles = [job['title'].lower() for job in jobs]
        
        # Verify false positives are filtered
        self.assertFalse(any('youtube' in t for t in titles))
        self.assertFalse(any('spotify' in t for t in titles))
        self.assertFalse(any('podcast' in t for t in titles))
        self.assertFalse(any('episode' in t for t in titles))
        
        # Verify the actual job is found
        self.assertTrue(any('architect' in t for t in titles),
                       "Solutions Architect should be extracted")

    def test_huble_false_positives(self):
        """Test false positives from huble.com/careers."""
        html = '''
        <html>
        <body>
            <h3>Marketing & Creative</h3>
            <h3>Sales & Revenue</h3>
            <h3><a href="/jobs/marketing-manager">Senior Marketing Manager</a></h3>
            <h3><a href="/jobs/sdr">Sales Development Representative</a></h3>
        </body>
        </html>
        '''
        
        extractor = MultiLayerExtractor("https://huble.com/careers")
        jobs = extractor.extract_all(html)
        
        titles = [job['title'] for job in jobs]
        
        # Department categories should not be extracted (no links, no descriptions)
        self.assertNotIn("Marketing & Creative", titles)
        self.assertNotIn("Sales & Revenue", titles)
        
        # Actual job titles with links should be extracted
        self.assertIn("Senior Marketing Manager", titles)
        self.assertIn("Sales Development Representative", titles)

    def test_mixed_actual_and_false_positives(self):
        """Test page with mix of actual jobs and false positives."""
        html = '''
        <html>
        <body>
            <h2>Open Positions</h2>
            <div class="jobs">
                <a href="/job/1">Senior HubSpot Developer</a>
                <a href="/job/2">RevOps Consultant</a>
                <a href="/blog">What Is HubSpot Development?</a>
                <a href="/apply">Apply Now</a>
                <a href="/team">Meet Our Team</a>
            </div>
        </body>
        </html>
        '''
        
        extractor = MultiLayerExtractor("https://example.com")
        jobs = extractor.extract_all(html)
        
        # Should extract exactly the 2 actual jobs
        self.assertEqual(len(jobs), 2, f"Should extract exactly 2 jobs, got {len(jobs)}")
        
        titles = [job['title'] for job in jobs]
        self.assertIn("Senior HubSpot Developer", titles)
        self.assertIn("RevOps Consultant", titles)


if __name__ == "__main__":
    unittest.main()
