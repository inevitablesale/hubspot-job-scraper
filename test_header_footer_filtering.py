"""
Tests for header/footer link filtering in career detector.
"""

import unittest
from career_detector import CareerPageDetector


class TestHeaderFooterFiltering(unittest.TestCase):
    """Test that header and footer links are properly filtered."""
    
    def setUp(self):
        self.detector = CareerPageDetector()
    
    def test_header_links_without_career_keywords_are_filtered(self):
        """Test that header links without career keywords are ignored."""
        html = """
        <html>
            <header>
                <nav>
                    <a href="/blog">Blog</a>
                    <a href="/about">About</a>
                    <a href="/contact">Contact</a>
                </nav>
            </header>
            <body>
                <a href="/team">Our Team</a>
            </body>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should not include blog, about, or contact from header
        assert not any("blog" in link for link in career_links)
        assert not any("about" in link for link in career_links)
        assert not any("contact" in link for link in career_links)
    
    def test_header_links_with_career_keywords_are_kept(self):
        """Test that header links with career keywords are kept."""
        html = """
        <html>
            <header>
                <nav>
                    <a href="/blog">Blog</a>
                    <a href="/careers">Careers</a>
                    <a href="/contact">Contact</a>
                </nav>
            </header>
            <body>
                <a href="/about">About</a>
            </body>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should include careers link even though it's in header
        assert any("careers" in link for link in career_links)
        
        # Should not include blog or contact
        assert not any("blog" in link for link in career_links)
        assert not any("contact" in link for link in career_links)
    
    def test_footer_links_without_career_keywords_are_filtered(self):
        """Test that footer links without career keywords are ignored."""
        html = """
        <html>
            <body>
                <a href="/services">Services</a>
            </body>
            <footer>
                <a href="https://facebook.com/company">Facebook</a>
                <a href="https://twitter.com/company">Twitter</a>
                <a href="/privacy">Privacy Policy</a>
                <a href="/terms">Terms</a>
            </footer>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should not include social or footer legal links
        assert not any("facebook" in link for link in career_links)
        assert not any("twitter" in link for link in career_links)
        assert not any("privacy" in link for link in career_links)
        assert not any("terms" in link for link in career_links)
    
    def test_footer_links_with_career_keywords_are_kept(self):
        """Test that footer links with career keywords are kept."""
        html = """
        <html>
            <body>
                <a href="/about">About</a>
            </body>
            <footer>
                <a href="/jobs">Jobs</a>
                <a href="/privacy">Privacy</a>
                <a href="https://linkedin.com/company/xyz">LinkedIn</a>
            </footer>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should include jobs link even though it's in footer
        assert any("jobs" in link for link in career_links)
        
        # Should not include privacy or linkedin (blacklisted)
        assert not any("privacy" in link for link in career_links)
        assert not any("linkedin" in link for link in career_links)
    
    def test_body_career_links_are_always_kept(self):
        """Test that career links in body are kept."""
        html = """
        <html>
            <header>
                <nav>
                    <a href="/home">Home</a>
                </nav>
            </header>
            <body>
                <section>
                    <h2>Join Our Team</h2>
                    <a href="/careers">View Open Positions</a>
                    <a href="/about/careers">Career Opportunities</a>
                </section>
            </body>
            <footer>
                <a href="/contact">Contact</a>
            </footer>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should find both career links from body
        assert len(career_links) >= 2
        assert any("careers" in link for link in career_links)
    
    def test_mixed_header_body_footer_links(self):
        """Test complex scenario with links in all sections."""
        html = """
        <html>
            <header>
                <nav>
                    <a href="/home">Home</a>
                    <a href="/about">About</a>
                    <a href="/careers">Careers</a>
                    <a href="/blog">Blog</a>
                </nav>
            </header>
            <body>
                <main>
                    <a href="/join-us">Join Our Team</a>
                    <a href="/services">Services</a>
                </main>
            </body>
            <footer>
                <a href="/jobs">Jobs</a>
                <a href="https://facebook.com/company">Facebook</a>
                <a href="/privacy">Privacy</a>
            </footer>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should include career-related links
        assert any("careers" in link for link in career_links)  # from header
        assert any("join-us" in link for link in career_links)  # from body
        assert any("jobs" in link for link in career_links)  # from footer
        
        # Should not include non-career links
        assert not any("blog" in link for link in career_links)
        assert not any("about" in link and "careers" not in link for link in career_links)
        assert not any("facebook" in link for link in career_links)
        assert not any("privacy" in link for link in career_links)
    
    def test_invalid_path_patterns_are_filtered(self):
        """Test that invalid path patterns are filtered even with career text."""
        html = """
        <html>
            <body>
                <a href="/blog/careers-in-tech">Blog post about careers</a>
                <a href="/resources/hiring-guide">Resources</a>
                <a href="/careers">Actual careers page</a>
            </body>
        </html>
        """
        
        career_links = self.detector.get_career_links(html, "https://example.com")
        
        # Should include actual careers page
        assert any(link.endswith("/careers") for link in career_links)
        
        # Should filter out blog even if it mentions careers
        blog_links = [link for link in career_links if "/blog" in link]
        assert len(blog_links) == 0, "Blog links should be filtered"


if __name__ == '__main__':
    unittest.main()
