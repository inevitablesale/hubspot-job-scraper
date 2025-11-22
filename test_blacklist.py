"""
Unit tests for the blacklist module.

Tests domain and category blacklisting functionality.
"""

import unittest
from blacklist import DomainBlacklist
from career_detector import CareerPageDetector
from scraper_engine import JobScraper


class TestDomainBlacklist(unittest.TestCase):
    """Test domain blacklist functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.blacklist = DomainBlacklist()
    
    def test_blacklisted_social_media_domains(self):
        """Test that social media domains are blacklisted."""
        social_domains = [
            "https://facebook.com/company",
            "https://www.facebook.com/company/page",
            "https://instagram.com/user",
            "https://linkedin.com/company/test",
            "https://twitter.com/user",
            "https://x.com/user",
            "https://youtube.com/channel/test",
            "https://tiktok.com/@user",
            "https://pinterest.com/user",
            "https://medium.com/@author",
        ]
        
        for url in social_domains:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to be blacklisted"
                )
    
    def test_blacklisted_publishing_platforms(self):
        """Test that publishing platforms are blacklisted."""
        publishing_domains = [
            "https://substack.com/newsletter",
            "https://blogger.com/blog",
            "https://wordpress.com/site",
            "https://wix.com/site",
            "https://squarespace.com/site",
        ]
        
        for url in publishing_domains:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to be blacklisted"
                )
    
    def test_blacklisted_hubspot_ecosystem(self):
        """Test that HubSpot ecosystem domains are blacklisted."""
        hubspot_domains = [
            "https://hubspot.com/",
            "https://app.hubspot.com/dashboard",
            "https://blog.hubspot.com/marketing",
            "https://help.hubspot.com/articles",
            "https://community.hubspot.com/forums",
        ]
        
        for url in hubspot_domains:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to be blacklisted"
                )
    
    def test_blacklisted_analytics_domains(self):
        """Test that analytics/tracking domains are blacklisted."""
        analytics_domains = [
            "https://google.com/search",
            "https://analytics.google.com/",
            "https://tagmanager.google.com/",
        ]
        
        for url in analytics_domains:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to be blacklisted"
                )
    
    def test_blacklisted_major_platforms(self):
        """Test that unrelated major platforms are blacklisted."""
        major_platforms = [
            "https://amazon.com/product",
            "https://aws.amazon.com/",
            "https://apple.com/",
            "https://microsoft.com/",
            "https://reddit.com/r/test",
            "https://quora.com/question",
        ]
        
        for url in major_platforms:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to be blacklisted"
                )
    
    def test_allowed_marketing_agency_domains(self):
        """Test that legitimate marketing agency domains are NOT blacklisted."""
        allowed_domains = [
            "https://smartbugmedia.com/careers",
            "https://impactplus.com/jobs",
            "https://webstacks.com/careers",
            "https://ironpaper.com/jobs",
            "https://salesfusion.com/careers",
            "https://revpartners.io/careers",
            "https://digitalmarketer.com/jobs",
            "https://modernmarketer.com/careers",
        ]
        
        for url in allowed_domains:
            with self.subTest(url=url):
                self.assertFalse(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to NOT be blacklisted"
                )
    
    def test_allowed_saas_company_domains(self):
        """Test that SaaS company domains are NOT blacklisted."""
        # Note: zendesk.com is blacklisted per problem statement requirements
        allowed_domains = [
            "https://slack.com/careers",
            "https://atlassian.com/jobs",
            "https://mailchimp.com/jobs",
            "https://freshworks.com/careers",
        ]
        
        for url in allowed_domains:
            with self.subTest(url=url):
                self.assertFalse(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} to NOT be blacklisted"
                )
    
    def test_subdomain_blacklisting(self):
        """Test that subdomains of blacklisted domains are also blacklisted."""
        subdomain_urls = [
            "https://careers.facebook.com/jobs",
            "https://business.linkedin.com/",
            "https://developer.twitter.com/",
            "https://support.hubspot.com/",
        ]
        
        for url in subdomain_urls:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected subdomain {url} to be blacklisted"
                )
    
    def test_www_prefix_handling(self):
        """Test that www. prefix is handled correctly."""
        urls_with_www = [
            "https://www.facebook.com/company",
            "https://www.instagram.com/user",
            "https://www.hubspot.com/",
        ]
        
        for url in urls_with_www:
            with self.subTest(url=url):
                self.assertTrue(
                    self.blacklist.is_blacklisted_domain(url),
                    f"Expected {url} (with www) to be blacklisted"
                )
    
    def test_get_blacklisted_domains(self):
        """Test that get_blacklisted_domains returns a copy of the set."""
        domains = self.blacklist.get_blacklisted_domains()
        
        # Verify it's a set
        self.assertIsInstance(domains, set)
        
        # Verify it contains expected domains
        self.assertIn("facebook.com", domains)
        self.assertIn("linkedin.com", domains)
        self.assertIn("hubspot.com", domains)
        
        # Verify it's a copy (modifying it doesn't affect the original)
        original_size = len(domains)
        domains.add("test.com")
        self.assertEqual(len(self.blacklist.get_blacklisted_domains()), original_size)
    
    def test_business_category_blacklisting(self):
        """Test that business categories are correctly identified as blacklisted."""
        blacklisted_categories = [
            "Restaurant",
            "Bar",
            "Cafe",
            "Gym",
            "Real Estate Agency",
            "Coworking Space",
            "Graphic Designer",
            "Plumber",
            "Auto Repair Shop",
        ]
        
        for category in blacklisted_categories:
            with self.subTest(category=category):
                self.assertTrue(
                    self.blacklist.is_blacklisted_category(category),
                    f"Expected {category} to be blacklisted"
                )
    
    def test_allowed_business_categories(self):
        """Test that relevant business categories are NOT blacklisted."""
        allowed_categories = [
            "Marketing Agency",
            "Software Company",
            "Consulting Firm",
            "Technology Company",
            "Digital Agency",
            "SaaS Provider",
        ]
        
        for category in allowed_categories:
            with self.subTest(category=category):
                self.assertFalse(
                    self.blacklist.is_blacklisted_category(category),
                    f"Expected {category} to NOT be blacklisted"
                )
    
    def test_get_blacklisted_categories(self):
        """Test that get_blacklisted_categories returns a copy of the set."""
        categories = self.blacklist.get_blacklisted_categories()
        
        # Verify it's a set
        self.assertIsInstance(categories, set)
        
        # Verify it contains expected categories
        self.assertIn("Restaurant", categories)
        self.assertIn("Gym", categories)
        self.assertIn("Real Estate Agency", categories)
        
        # Verify it's a copy
        original_size = len(categories)
        categories.add("Test Category")
        self.assertEqual(len(self.blacklist.get_blacklisted_categories()), original_size)


class TestCareerDetectorBlacklist(unittest.TestCase):
    """Test that CareerPageDetector respects the blacklist."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = CareerPageDetector()
    
    def test_filters_blacklisted_career_links(self):
        """Test that get_career_links filters out blacklisted domains."""
        html = """
        <html>
            <body>
                <a href="https://facebook.com/company/careers">Careers on Facebook</a>
                <a href="https://company.com/careers">Company Careers</a>
                <a href="https://linkedin.com/company/jobs">Jobs on LinkedIn</a>
                <a href="https://company.com/jobs">Company Jobs</a>
                <a href="https://hubspot.com/careers">HubSpot Careers</a>
            </body>
        </html>
        """
        
        links = self.detector.get_career_links(html, "https://company.com")
        
        # Should only include company.com links, not blacklisted domains
        self.assertEqual(len(links), 2)
        self.assertIn("https://company.com/careers", links)
        self.assertIn("https://company.com/jobs", links)
        
        # Should not include blacklisted domains
        for link in links:
            self.assertNotIn("facebook.com", link)
            self.assertNotIn("linkedin.com", link)
            self.assertNotIn("hubspot.com", link)


class TestScraperEngineBlacklist(unittest.TestCase):
    """Test that ScraperEngine respects the blacklist."""
    
    def test_should_skip_blacklisted_domains(self):
        """Test that _should_skip_domain correctly identifies blacklisted domains."""
        scraper = JobScraper()
        
        # Test blacklisted domains
        blacklisted = [
            "https://facebook.com/page",
            "https://linkedin.com/company",
            "https://twitter.com/user",
            "https://hubspot.com/product",
            "https://google.com/search",
        ]
        
        for url in blacklisted:
            with self.subTest(url=url):
                self.assertTrue(
                    scraper._should_skip_domain(url),
                    f"Expected {url} to be skipped"
                )
    
    def test_should_not_skip_allowed_domains(self):
        """Test that legitimate domains are not skipped."""
        scraper = JobScraper()
        
        # Test allowed domains
        allowed = [
            "https://marketingagency.com/careers",
            "https://saascompany.com/jobs",
            "https://revopsagency.com/careers",
            "https://digitalagency.com/jobs",
        ]
        
        for url in allowed:
            with self.subTest(url=url):
                self.assertFalse(
                    scraper._should_skip_domain(url),
                    f"Expected {url} to NOT be skipped"
                )


if __name__ == '__main__':
    unittest.main()
