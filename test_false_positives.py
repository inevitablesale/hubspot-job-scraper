"""
Test to reproduce and fix false positive job extractions.

This tests the issues seen in production where non-job content
is being extracted as jobs.
"""

import unittest
from extractors import MultiLayerExtractor, AnchorExtractor, HeadingExtractor


class TestFalsePositives(unittest.TestCase):
    """Test that false positives are not extracted as jobs."""

    def test_blog_posts_not_extracted(self):
        """Blog posts mentioning job keywords should not be extracted."""
        html = '''
        <html>
        <body>
            <a href="/blog/what-is-inbound-marketing">What Is Inbound Marketing?</a>
            <a href="/blog/content-marketing-guide">What Is Content Marketing?</a>
            <a href="/resources/marketing-tips">Inbound Marketing & Strategic Content</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # These should NOT be extracted as jobs
        self.assertEqual(len(jobs), 0, "Blog posts should not be extracted as jobs")

    def test_navigation_links_not_extracted(self):
        """Generic navigation links should not be extracted."""
        html = '''
        <html>
        <body>
            <a href="/about">About Us</a>
            <a href="/services">Our Services</a>
            <a href="/contact">Contact Sales</a>
            <a href="/team">Meet Our Team</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Navigation links without actual job titles should not be extracted
        self.assertEqual(len(jobs), 0, "Generic navigation should not be extracted")

    def test_social_media_links_not_extracted(self):
        """Social media and generic CTAs should not be extracted."""
        html = '''
        <html>
        <body>
            <a href="https://youtube.com/watch?v=123">Watch On Youtube</a>
            <a href="https://podcasts.apple.com/podcast/123">Apple Podcasts Listen On Apple Podcasts</a>
            <a href="https://spotify.com/show/123">Spotify Listen On Spotify</a>
            <a href="/apply">Apply Today</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Social media links should not be extracted
        for job in jobs:
            self.assertNotIn("youtube", job['title'].lower())
            self.assertNotIn("spotify", job['title'].lower())
            self.assertNotIn("podcast", job['title'].lower())

    def test_department_categories_not_extracted(self):
        """Department categories without specific job titles should not be extracted."""
        html = '''
        <html>
        <body>
            <a href="/careers#marketing">Marketing & Creative</a>
            <a href="/careers#sales">Sales & Revenue</a>
            <a href="/careers#engineering">Engineering & Product</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Generic department categories are not job titles
        # These might be extracted, but they should be very short and vague
        # We'll filter them by requiring more specific job title patterns
        for job in jobs:
            # Job titles should be more specific than just "Marketing & Creative"
            title_words = job['title'].split()
            # If it's just 2-3 generic words, it's likely a category, not a job
            if len(title_words) <= 3:
                has_role_word = any(word.lower() in ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'consultant', 'architect'] for word in title_words)
                if not has_role_word:
                    self.fail(f"Category '{job['title']}' should not be extracted as a job")

    def test_actual_jobs_are_extracted(self):
        """Verify that actual job postings are still extracted."""
        html = '''
        <html>
        <body>
            <h2>Open Positions</h2>
            <a href="/jobs/senior-developer">Senior HubSpot Developer</a>
            <a href="/jobs/consultant">HubSpot Solutions Consultant</a>
            <a href="/jobs/architect">Solutions Architect</a>
        </body>
        </html>
        '''
        extractor = MultiLayerExtractor("https://example.com")
        jobs = extractor.extract_all(html)
        
        # Should find actual job postings
        self.assertGreater(len(jobs), 0, "Actual jobs should be extracted")
        
        # Check that we got the right jobs
        titles = [job['title'].lower() for job in jobs]
        self.assertTrue(any('developer' in t for t in titles))

    def test_question_format_not_extracted(self):
        """Questions/articles about topics should not be jobs."""
        html = '''
        <html>
        <body>
            <h3>What is a Marketing Manager?</h3>
            <h3>How to Become a Developer</h3>
            <h3>Why Choose a Career in Sales?</h3>
        </body>
        </html>
        '''
        extractor = HeadingExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Questions should not be extracted as jobs
        for job in jobs:
            title_lower = job['title'].lower()
            self.assertFalse(title_lower.startswith('what'), f"Question '{job['title']}' should not be a job")
            self.assertFalse(title_lower.startswith('how'), f"Question '{job['title']}' should not be a job")
            self.assertFalse(title_lower.startswith('why'), f"Question '{job['title']}' should not be a job")

    def test_generic_ctas_not_extracted(self):
        """Generic CTAs without role info should not be extracted."""
        html = '''
        <html>
        <body>
            <a href="/careers">Join Our Team</a>
            <a href="/careers">View Openings</a>
            <a href="/apply">Apply Now</a>
            <a href="/careers">See All Jobs</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # These are CTAs, not actual job titles
        # They should not be extracted
        self.assertEqual(len(jobs), 0, "Generic CTAs should not be extracted as jobs")


if __name__ == "__main__":
    unittest.main()
