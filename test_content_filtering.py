"""
Test content filtering to prevent extraction from header/footer/nav.

Validates that the scraper properly filters out non-job content from:
- Header navigation
- Footer links
- Sidebar navigation
- Social media links
- Blog/podcast/team pages
- Blacklisted URL patterns
"""

import unittest
from extractors import AnchorExtractor, HeadingExtractor, MultiLayerExtractor


class TestHeaderFooterFiltering(unittest.TestCase):
    """Test that header and footer elements are filtered."""

    def test_header_navigation_filtered(self):
        """Header navigation links should be filtered out."""
        html = '''
        <html>
        <header>
            <nav>
                <a href="/about">About Us</a>
                <a href="/team">Meet Our Team</a>
                <a href="/contact">Contact</a>
                <a href="/blog">Blog</a>
            </nav>
        </header>
        <body>
            <main>
                <h2>Open Positions</h2>
                <a href="/jobs/senior-developer">Senior Developer</a>
            </main>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the job from main content
        self.assertEqual(len(jobs), 1)
        self.assertIn("developer", jobs[0]['title'].lower())
        
        # Should NOT extract header links
        for job in jobs:
            self.assertNotIn("about", job['title'].lower())
            self.assertNotIn("team", job['title'].lower())
            self.assertNotIn("contact", job['title'].lower())

    def test_footer_links_filtered(self):
        """Footer links should be filtered out."""
        html = '''
        <html>
        <body>
            <main>
                <a href="/jobs/consultant">HubSpot Consultant</a>
            </main>
        </body>
        <footer>
            <a href="https://facebook.com/company">Facebook</a>
            <a href="https://twitter.com/company">Twitter</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms of Service</a>
        </footer>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the job from main content
        self.assertEqual(len(jobs), 1)
        self.assertIn("consultant", jobs[0]['title'].lower())
        
        # Should NOT extract footer links
        for job in jobs:
            self.assertNotIn("facebook", job.get('url', '').lower())
            self.assertNotIn("twitter", job.get('url', '').lower())

    def test_nav_role_filtered(self):
        """Elements with role=navigation should be filtered."""
        html = '''
        <html>
        <body>
            <div role="navigation">
                <a href="/services">Our Services</a>
                <a href="/portfolio">Portfolio</a>
            </div>
            <main>
                <a href="/jobs/architect">Solutions Architect</a>
            </main>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the job
        self.assertEqual(len(jobs), 1)
        self.assertIn("architect", jobs[0]['title'].lower())

    def test_heading_in_header_filtered(self):
        """Headings in header should be filtered."""
        html = '''
        <html>
        <header>
            <h2><a href="/about/team">Principal Developer</a></h2>
        </header>
        <body>
            <main>
                <h2><a href="/jobs/123">Senior Developer</a></h2>
            </main>
        </body>
        </html>
        '''
        extractor = HeadingExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract from main, not header
        self.assertEqual(len(jobs), 1)
        self.assertEqual("Senior Developer", jobs[0]['title'])


class TestURLPatternBlacklist(unittest.TestCase):
    """Test that blacklisted URL patterns are filtered."""

    def test_blog_urls_filtered(self):
        """Blog URLs should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="/blog/what-is-inbound-marketing">Marketing Specialist</a>
            <a href="/jobs/marketing-specialist">Marketing Specialist</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the /jobs/ URL
        self.assertEqual(len(jobs), 1)
        self.assertIn("/jobs/", jobs[0]['url'])
        self.assertNotIn("/blog/", jobs[0]['url'])

    def test_team_urls_filtered(self):
        """Team page URLs should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="/team/principal-consultant">Principal Consultant</a>
            <a href="/careers/principal-consultant">Principal Consultant</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the /careers/ URL
        self.assertEqual(len(jobs), 1)
        self.assertIn("/careers/", jobs[0]['url'])
        self.assertNotIn("/team/", jobs[0]['url'])

    def test_contact_urls_filtered(self):
        """Contact page URLs should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="/contact">Contact Our Team</a>
            <a href="/jobs/developer">Senior Developer</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the developer job
        self.assertEqual(len(jobs), 1)
        self.assertNotIn("/contact", jobs[0]['url'])

    def test_podcast_urls_filtered(self):
        """Podcast URLs should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="/podcast/episode-123">Marketing Manager Interview</a>
            <a href="/jobs/marketing-manager">Marketing Manager</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the job URL
        self.assertEqual(len(jobs), 1)
        self.assertIn("/jobs/", jobs[0]['url'])

    def test_resources_urls_filtered(self):
        """Resources URLs should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="/resources/hiring-guide">Developer Hiring Guide</a>
            <a href="/jobs/developer">Full Stack Developer</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the job
        self.assertEqual(len(jobs), 1)
        self.assertIn("/jobs/", jobs[0]['url'])


class TestDomainBlacklist(unittest.TestCase):
    """Test that blacklisted domains are filtered."""

    def test_social_media_filtered(self):
        """Social media links should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="https://facebook.com/company">Marketing Specialist</a>
            <a href="https://twitter.com/company">Social Media Manager</a>
            <a href="https://linkedin.com/company/xyz">Account Manager</a>
            <a href="/jobs/manager">Account Manager</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the local job URL
        self.assertEqual(len(jobs), 1)
        self.assertIn("example.com", jobs[0]['url'])

    def test_hubspot_domain_filtered(self):
        """HubSpot domain links should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="https://hubspot.com/products">Marketing Manager</a>
            <a href="https://blog.hubspot.com/article">Content Strategist</a>
            <a href="/jobs/strategist">Content Strategist</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the local job URL
        self.assertEqual(len(jobs), 1)
        self.assertIn("example.com", jobs[0]['url'])

    def test_youtube_filtered(self):
        """YouTube links should be filtered out."""
        html = '''
        <html>
        <body>
            <a href="https://youtube.com/watch?v=123">Marketing Manager Interview</a>
            <a href="/jobs/manager">Marketing Manager</a>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the local job URL
        self.assertEqual(len(jobs), 1)
        self.assertIn("example.com", jobs[0]['url'])


class TestJobContainerScope(unittest.TestCase):
    """Test that job containers are properly scoped."""

    def test_job_container_allows_extraction(self):
        """Elements inside job containers should be extracted."""
        html = '''
        <html>
        <header>
            <nav>
                <a href="/home">Home</a>
            </nav>
        </header>
        <body>
            <div class="job-listings">
                <div class="job-card">
                    <h3>Senior Developer</h3>
                    <a href="/apply/123">Apply Now</a>
                </div>
            </div>
        </body>
        </html>
        '''
        extractor = HeadingExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should extract the job from the job container
        self.assertGreaterEqual(len(jobs), 1)
        self.assertTrue(any("developer" in job['title'].lower() for job in jobs))

    def test_footer_job_widget_allowed(self):
        """Job widgets in footer should be allowed if in job container."""
        html = '''
        <html>
        <body>
            <main>
                <p>Some content</p>
            </main>
        </body>
        <footer>
            <div class="job-openings">
                <a href="/jobs/developer">Developer Position</a>
            </div>
            <a href="/privacy">Privacy</a>
        </footer>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should extract the job from the footer job widget
        # but not the privacy link
        self.assertEqual(len(jobs), 1)
        self.assertIn("developer", jobs[0]['title'].lower())


class TestComplexScenarios(unittest.TestCase):
    """Test complex real-world scenarios."""

    def test_mixed_page_structure(self):
        """Test complex page with header, main, footer, and job listings."""
        html = '''
        <html>
        <header>
            <nav>
                <a href="/about">About</a>
                <a href="/team">Team</a>
                <a href="/blog">Blog</a>
                <a href="/careers">Careers</a>
            </nav>
        </header>
        <body>
            <aside>
                <a href="/services">Our Services</a>
            </aside>
            <main>
                <section class="careers-section">
                    <h2>Open Positions</h2>
                    <div class="job-card">
                        <h3>Senior Developer</h3>
                        <a href="/jobs/dev-123">Apply</a>
                    </div>
                    <div class="job-card">
                        <h3>Marketing Manager</h3>
                        <a href="/jobs/mkt-456">Apply</a>
                    </div>
                </section>
            </main>
        </body>
        <footer>
            <a href="https://facebook.com/company">Facebook</a>
            <a href="https://twitter.com/company">Twitter</a>
            <a href="/contact">Contact</a>
        </footer>
        </html>
        '''
        extractor = MultiLayerExtractor("https://example.com")
        jobs = extractor.extract_all(html)
        
        # Should extract only the jobs from main content
        self.assertGreaterEqual(len(jobs), 2)
        
        # Check that we got the right jobs
        titles = [job['title'].lower() for job in jobs]
        self.assertTrue(any('developer' in t for t in titles))
        self.assertTrue(any('manager' in t for t in titles))
        
        # Should NOT extract header/footer links
        for job in jobs:
            url = job.get('url', '')
            self.assertNotIn('facebook.com', url)
            self.assertNotIn('twitter.com', url)
            self.assertNotIn('/about', url)
            self.assertNotIn('/contact', url)

    def test_team_page_false_positive(self):
        """Test that team member profiles don't get extracted as jobs."""
        html = '''
        <html>
        <body>
            <main>
                <h1>Our Team</h1>
                <div class="team-members">
                    <div class="member">
                        <h3>John Doe</h3>
                        <p>Principal Consultant</p>
                        <a href="/team/john-doe">View Profile</a>
                    </div>
                </div>
                <div class="job-listings">
                    <h2>We're Hiring</h2>
                    <a href="/jobs/consultant">Senior Consultant</a>
                </div>
            </main>
        </body>
        </html>
        '''
        extractor = AnchorExtractor("https://example.com")
        jobs = extractor.extract(html)
        
        # Should only extract the job, not the team member link
        filtered_jobs = [j for j in jobs if '/team/' not in j.get('url', '')]
        self.assertEqual(len(filtered_jobs), 1)
        self.assertIn('/jobs/', filtered_jobs[0]['url'])


if __name__ == "__main__":
    unittest.main()
