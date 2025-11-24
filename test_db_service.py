"""
Tests for database service functionality.

These tests verify the database service without requiring an actual Supabase connection.
They test the logic and structure of database operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from db_service import DatabaseService
from db_models import Company, Job, JobMetadata, ATSSource, ScrapeRun, JobHistory


class TestDatabaseService:
    """Test suite for DatabaseService."""
    
    def test_init_without_supabase(self):
        """Test that service initializes gracefully without Supabase."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            assert service.enabled is False
            assert service.client is None
    
    def test_init_with_supabase(self):
        """Test that service initializes correctly with Supabase."""
        mock_client = Mock()
        with patch('db_service.get_supabase_client', return_value=mock_client):
            service = DatabaseService()
            assert service.enabled is True
            assert service.client == mock_client
    
    def test_is_enabled_returns_false_without_client(self):
        """Test _is_enabled returns False when client is None."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            assert service._is_enabled() is False
    
    def test_is_enabled_returns_true_with_client(self):
        """Test _is_enabled returns True when client exists."""
        mock_client = Mock()
        with patch('db_service.get_supabase_client', return_value=mock_client):
            service = DatabaseService()
            assert service._is_enabled() is True
    
    def test_calculate_job_hash(self):
        """Test job hash calculation."""
        mock_client = Mock()
        with patch('db_service.get_supabase_client', return_value=mock_client):
            service = DatabaseService()
            
            company_id = uuid4()
            job_title = "Software Engineer"
            job_url = "https://example.com/jobs/123"
            
            hash1 = service._calculate_job_hash(job_title, company_id, job_url)
            hash2 = service._calculate_job_hash(job_title, company_id, job_url)
            
            # Same inputs should produce same hash
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 produces 64-character hex string
            
            # Different inputs should produce different hash
            hash3 = service._calculate_job_hash("Different Title", company_id, job_url)
            assert hash1 != hash3
    
    def test_get_or_create_company_without_db(self):
        """Test get_or_create_company returns None when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.get_or_create_company("Test Co", "test.com", "https://test.com")
            assert result is None
    
    def test_get_or_create_job_without_db(self):
        """Test get_or_create_job returns None when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.get_or_create_job(
                company_id=uuid4(),
                job_title="Engineer",
                job_url="https://example.com/job"
            )
            assert result is None
    
    def test_insert_job_metadata_without_db(self):
        """Test insert_job_metadata returns False when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.insert_job_metadata(
                job_id=uuid4(),
                seniority="senior"
            )
            assert result is False
    
    def test_insert_job_metadata_skips_when_no_data(self):
        """Test insert_job_metadata skips when no meaningful data provided."""
        mock_client = Mock()
        with patch('db_service.get_supabase_client', return_value=mock_client):
            service = DatabaseService()
            
            # Should return True but not call insert
            result = service.insert_job_metadata(job_id=uuid4())
            assert result is True
            assert not mock_client.table.called
    
    def test_insert_ats_source_without_db(self):
        """Test insert_ats_source returns False when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.insert_ats_source(
                job_id=uuid4(),
                provider="greenhouse"
            )
            assert result is False
    
    def test_create_scrape_run_without_db(self):
        """Test create_scrape_run returns None when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.create_scrape_run()
            assert result is None
    
    def test_update_scrape_run_without_db(self):
        """Test update_scrape_run returns False when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.update_scrape_run(
                run_id=uuid4(),
                total_companies=10,
                total_jobs=50
            )
            assert result is False
    
    def test_insert_job_history_without_db(self):
        """Test insert_job_history returns False when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.insert_job_history(
                job_id=uuid4(),
                snapshot={"title": "Engineer"}
            )
            assert result is False
    
    def test_save_scraped_job_without_db(self):
        """Test save_scraped_job returns None when DB not configured."""
        with patch('db_service.get_supabase_client', return_value=None):
            service = DatabaseService()
            result = service.save_scraped_job(
                company_name="Test Co",
                company_domain="test.com",
                company_source_url="https://test.com",
                job_data={"title": "Engineer", "url": "https://test.com/job"}
            )
            assert result is None


class TestDatabaseModels:
    """Test suite for database models."""
    
    def test_company_model_defaults(self):
        """Test Company model creates with proper defaults."""
        company = Company(
            name="Test Company",
            domain="test.com",
            source_url="https://test.com"
        )
        
        assert company.name == "Test Company"
        assert company.domain == "test.com"
        assert company.source_url == "https://test.com"
        assert company.logo_url is None
        assert isinstance(company.id, type(uuid4()))
        assert isinstance(company.created_at, datetime)
        assert isinstance(company.updated_at, datetime)
    
    def test_job_model_defaults(self):
        """Test Job model creates with proper defaults."""
        company_id = uuid4()
        job = Job(
            company_id=company_id,
            job_title="Software Engineer",
            job_url="https://example.com/job",
            hash="test_hash"
        )
        
        assert job.company_id == company_id
        assert job.job_title == "Software Engineer"
        assert job.job_url == "https://example.com/job"
        assert job.hash == "test_hash"
        assert job.active is True
        assert job.department is None
        assert job.location is None
        assert isinstance(job.id, type(uuid4()))
        assert isinstance(job.scraped_at, datetime)
    
    def test_job_metadata_model(self):
        """Test JobMetadata model."""
        job_id = uuid4()
        metadata = JobMetadata(
            job_id=job_id,
            seniority="senior",
            employment_type="full_time",
            technologies=["Python", "PostgreSQL"]
        )
        
        assert metadata.job_id == job_id
        assert metadata.seniority == "senior"
        assert metadata.employment_type == "full_time"
        assert metadata.technologies == ["Python", "PostgreSQL"]
        assert metadata.salary_min is None
        assert metadata.salary_max is None
    
    def test_ats_source_model(self):
        """Test ATSSource model."""
        job_id = uuid4()
        ats = ATSSource(
            job_id=job_id,
            provider="greenhouse"
        )
        
        assert ats.job_id == job_id
        assert ats.provider == "greenhouse"
        assert ats.raw_html is None
        assert isinstance(ats.detected_at, datetime)
    
    def test_scrape_run_model(self):
        """Test ScrapeRun model."""
        run = ScrapeRun()
        
        assert run.total_companies == 0
        assert run.total_jobs == 0
        assert run.finished_at is None
        assert run.errors is None
        assert isinstance(run.started_at, datetime)
    
    def test_job_history_model(self):
        """Test JobHistory model."""
        job_id = uuid4()
        snapshot = {"title": "Engineer", "location": "Remote"}
        history = JobHistory(
            job_id=job_id,
            snapshot=snapshot
        )
        
        assert history.job_id == job_id
        assert history.snapshot == snapshot
        assert isinstance(history.captured_at, datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
