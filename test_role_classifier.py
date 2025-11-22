"""
Tests for role classification and scoring engine.
"""

import unittest
from role_classifier import RoleClassifier


class TestRoleClassifier(unittest.TestCase):
    """Test role classification and scoring."""

    def setUp(self):
        self.classifier = RoleClassifier()

    def test_classify_developer_role(self):
        """Test classification of developer role."""
        content = """
        HubSpot CMS Developer position
        We are looking for a developer experienced with HubSpot CMS Hub,
        custom modules, theme development, and HubSpot API integrations.
        Strong JavaScript and React skills required.
        """
        job_data = {"title": "HubSpot Developer", "url": "https://example.com/job/1"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'developer')
        self.assertGreaterEqual(result['score'], 60)
        self.assertIn('signals', result)

    def test_classify_consultant_role(self):
        """Test classification of consultant role."""
        content = """
        HubSpot Consultant needed
        RevOps specialist with experience in HubSpot workflows,
        automation, CRM migration, and onboarding implementations.
        Marketing ops background preferred.
        """
        job_data = {"title": "HubSpot Consultant", "url": "https://example.com/job/2"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'consultant')
        self.assertGreaterEqual(result['score'], 50)

    def test_architect_detection(self):
        """Test architect role detection and boosting."""
        content = """
        Solutions Architect for HubSpot
        We need a technical architect to design HubSpot implementations,
        integrations, and custom workflows for enterprise clients.
        """
        job_data = {"title": "Solutions Architect", "url": "https://example.com/job/3"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'architect')
        self.assertGreater(result['score'], 50)

    def test_senior_consultant_detection(self):
        """Test senior consultant detection."""
        content = """
        Senior HubSpot Consultant
        Lead consultant role focusing on RevOps and HubSpot implementation.
        Consultant certification required.
        """
        job_data = {"title": "Senior Consultant", "url": "https://example.com/job/4"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'senior_consultant')

    def test_remote_detection(self):
        """Test remote work detection."""
        content = """
        Remote HubSpot Developer
        Work from anywhere with our distributed team.
        HubSpot API and CMS Hub experience required.
        """
        job_data = {"title": "Remote Developer", "url": "https://example.com/job/5"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['location_type'], 'remote')
        self.assertIn('Remote-friendly', result['signals'])

    def test_hybrid_detection(self):
        """Test hybrid work detection."""
        content = """
        HubSpot Consultant - Hybrid
        Flexible work arrangement with office optional.
        HubSpot workflows and automation expertise needed.
        """
        job_data = {"title": "Consultant", "url": "https://example.com/job/6"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['location_type'], 'hybrid')

    def test_contract_detection(self):
        """Test contract/1099 detection."""
        content = """
        Contract HubSpot Developer
        1099 independent contractor position.
        HubSpot CMS Hub and API experience required.
        Build custom modules and integrations.
        """
        job_data = {"title": "Contract Developer", "url": "https://example.com/job/7"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertTrue(result['is_contract'])
        self.assertIn('1099/Contract', result['signals'])

    def test_filters_non_hubspot_roles(self):
        """Test that non-HubSpot roles are filtered."""
        content = """
        Senior Software Engineer
        We need a React developer for our web application.
        No HubSpot experience needed.
        """
        job_data = {"title": "Software Engineer", "url": "https://example.com/job/8"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        # Should return None because it lacks HubSpot keywords
        self.assertIsNone(result)

    def test_filters_low_scoring_roles(self):
        """Test that low-scoring roles are filtered."""
        content = """
        HubSpot mentioned once
        Generic role with minimal HubSpot relevance.
        """
        job_data = {"title": "Generic Role", "url": "https://example.com/job/9"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        # Should return None because score is below threshold
        self.assertIsNone(result)

    def test_strong_hubspot_signals_boost(self):
        """Test that strong HubSpot signals boost the score."""
        content = """
        HubSpot Certified Developer
        HubSpot Elite Partner agency seeking developer.
        Custom object and serverless functions experience.
        HubSpot API integrations required.
        """
        job_data = {"title": "HubSpot Developer", "url": "https://example.com/job/10"}
        
        result = self.classifier.classify_and_score(content.lower(), job_data)
        
        self.assertIsNotNone(result)
        self.assertGreater(result['score'], 60)
        self.assertIn('Strong HubSpot Expertise Signal', result['signals'])


class TestRoleFilters(unittest.TestCase):
    """Test role filtering logic."""

    def setUp(self):
        self.classifier = RoleClassifier()

    def test_should_include_role_no_filters(self):
        """Test role inclusion when no filters are set."""
        import os
        os.environ.pop('ROLE_FILTER', None)
        os.environ.pop('REMOTE_ONLY', None)
        
        self.assertTrue(self.classifier.should_include_role('developer', 'remote'))
        self.assertTrue(self.classifier.should_include_role('consultant', 'onsite'))

    def test_role_filter(self):
        """Test role filtering."""
        import os
        os.environ['ROLE_FILTER'] = 'developer,architect'
        
        # Create a new classifier to pick up env var
        classifier = RoleClassifier()
        
        self.assertTrue(classifier.should_include_role('developer', 'remote'))
        self.assertTrue(classifier.should_include_role('architect', 'remote'))
        self.assertFalse(classifier.should_include_role('consultant', 'remote'))
        
        # Clean up
        os.environ.pop('ROLE_FILTER', None)

    def test_remote_only_filter(self):
        """Test remote-only filtering."""
        import os
        os.environ['REMOTE_ONLY'] = 'true'
        
        # Create a new classifier to pick up env var
        classifier = RoleClassifier()
        
        self.assertTrue(classifier.should_include_role('developer', 'remote'))
        self.assertFalse(classifier.should_include_role('developer', 'onsite'))
        self.assertFalse(classifier.should_include_role('developer', 'hybrid'))
        
        # Clean up
        os.environ.pop('REMOTE_ONLY', None)


if __name__ == "__main__":
    unittest.main()
