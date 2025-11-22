"""
Test suite for the API server implementation.

Tests the proposed API design and validates all endpoints.
"""

import asyncio
import json
from datetime import datetime
from fastapi.testclient import TestClient

# Import the API server
from api_server import app
from models import CrawlSummary, JobItem, DomainItem, ConfigSettings, LogLine, CrawlEvent
from state import crawler_state, config_state, events_bus, logs_buffer


def test_health_check():
    """Test the health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data


def test_get_summary():
    """Test getting the crawl summary."""
    client = TestClient(app)
    response = client.get("/api/system/summary")
    assert response.status_code == 200
    
    # Validate response matches CrawlSummary model
    summary = CrawlSummary(**response.json())
    assert summary.state in ["idle", "running", "stopping", "error", "finished"]
    assert isinstance(summary.domains_total, int)
    assert isinstance(summary.jobs_found, int)


def test_start_crawl_when_idle():
    """Test starting a crawl when idle."""
    client = TestClient(app)
    
    # Ensure crawler is idle
    crawler_state._state = "idle"
    
    response = client.post("/api/crawl/start")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is True
    assert "message" in data


def test_start_crawl_when_running():
    """Test starting a crawl when already running."""
    client = TestClient(app)
    
    # Set crawler to running
    crawler_state._state = "running"
    
    response = client.post("/api/crawl/start")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is False
    assert data["reason"] == "already_running"


def test_stop_crawl():
    """Test stopping a running crawl."""
    client = TestClient(app)
    
    # Set crawler to running
    crawler_state._state = "running"
    
    response = client.post("/api/crawl/stop")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is True
    assert crawler_state._state == "stopping"


def test_stop_crawl_when_not_running():
    """Test stopping when not running."""
    client = TestClient(app)
    
    # Set crawler to idle
    crawler_state._state = "idle"
    
    response = client.post("/api/crawl/stop")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is False
    assert data["reason"] == "not_running"


def test_get_logs():
    """Test getting logs."""
    client = TestClient(app)
    
    # Add some test logs
    logs_buffer.clear()
    for i in range(10):
        logs_buffer.append(LogLine(
            ts=datetime.utcnow(),
            level="info",
            message=f"Test log {i}",
            source="crawler"
        ))
    
    response = client.get("/api/logs?limit=5")
    assert response.status_code == 200
    
    logs = response.json()
    assert len(logs) <= 5


def test_list_jobs_empty():
    """Test listing jobs when none exist."""
    client = TestClient(app)
    
    # Clear jobs
    crawler_state._jobs = []
    
    response = client.get("/api/jobs")
    assert response.status_code == 200
    
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) == 0


def test_list_jobs_with_data():
    """Test listing jobs with data."""
    client = TestClient(app)
    
    # Add test jobs
    crawler_state._jobs = [
        JobItem(
            id="job1",
            domain="example.com",
            title="Software Engineer",
            url="https://example.com/job1",
            source_page="https://example.com/careers",
            created_at=datetime.utcnow()
        ),
        JobItem(
            id="job2",
            domain="test.com",
            title="Data Scientist",
            location="Remote",
            remote_type="remote",
            url="https://test.com/job2",
            source_page="https://test.com/careers",
            created_at=datetime.utcnow()
        )
    ]
    
    response = client.get("/api/jobs")
    assert response.status_code == 200
    
    jobs = response.json()
    assert len(jobs) == 2
    assert jobs[0]["id"] == "job1"
    assert jobs[1]["id"] == "job2"


def test_list_jobs_with_query():
    """Test filtering jobs by query."""
    client = TestClient(app)
    
    # Add test jobs
    crawler_state._jobs = [
        JobItem(
            id="job1",
            domain="example.com",
            title="Software Engineer",
            url="https://example.com/job1",
            source_page="https://example.com/careers",
            created_at=datetime.utcnow()
        ),
        JobItem(
            id="job2",
            domain="test.com",
            title="Data Scientist",
            url="https://test.com/job2",
            source_page="https://test.com/careers",
            created_at=datetime.utcnow()
        )
    ]
    
    response = client.get("/api/jobs?q=engineer")
    assert response.status_code == 200
    
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer"


def test_list_jobs_remote_only():
    """Test filtering remote-only jobs."""
    client = TestClient(app)
    
    # Add test jobs
    crawler_state._jobs = [
        JobItem(
            id="job1",
            domain="example.com",
            title="Software Engineer",
            remote_type="office",
            url="https://example.com/job1",
            source_page="https://example.com/careers",
            created_at=datetime.utcnow()
        ),
        JobItem(
            id="job2",
            domain="test.com",
            title="Data Scientist",
            remote_type="remote",
            url="https://test.com/job2",
            source_page="https://test.com/careers",
            created_at=datetime.utcnow()
        )
    ]
    
    response = client.get("/api/jobs?remote_only=true")
    assert response.status_code == 200
    
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["remote_type"] == "remote"


def test_get_job_detail():
    """Test getting a specific job."""
    client = TestClient(app)
    
    # Add a test job
    crawler_state._jobs = [
        JobItem(
            id="job1",
            domain="example.com",
            title="Software Engineer",
            url="https://example.com/job1",
            source_page="https://example.com/careers",
            created_at=datetime.utcnow()
        )
    ]
    
    response = client.get("/api/jobs/job1")
    assert response.status_code == 200
    
    job = response.json()
    assert job["id"] == "job1"
    assert job["title"] == "Software Engineer"


def test_get_job_not_found():
    """Test getting a job that doesn't exist."""
    client = TestClient(app)
    
    crawler_state._jobs = []
    
    response = client.get("/api/jobs/nonexistent")
    assert response.status_code == 404


def test_list_domains():
    """Test listing domains."""
    client = TestClient(app)
    
    # Add test domains
    crawler_state._domains = [
        DomainItem(
            domain="example.com",
            category="Tech",
            blacklisted=False,
            jobs_count=5,
            status="completed"
        ),
        DomainItem(
            domain="test.com",
            category="Finance",
            blacklisted=False,
            jobs_count=3,
            status="in_progress"
        )
    ]
    
    response = client.get("/api/domains")
    assert response.status_code == 200
    
    domains = response.json()
    assert len(domains) == 2
    assert domains[0]["domain"] == "example.com"


def test_get_domain_detail():
    """Test getting domain details."""
    client = TestClient(app)
    
    crawler_state._domains = [
        DomainItem(
            domain="example.com",
            category="Tech",
            blacklisted=False,
            jobs_count=5,
            status="completed"
        )
    ]
    
    response = client.get("/api/domains/example.com")
    assert response.status_code == 200
    
    domain = response.json()
    assert domain["domain"] == "example.com"
    assert domain["jobs_count"] == 5


def test_get_domain_not_found():
    """Test getting a domain that doesn't exist."""
    client = TestClient(app)
    
    crawler_state._domains = []
    
    response = client.get("/api/domains/nonexistent.com")
    assert response.status_code == 404


def test_get_config():
    """Test getting configuration."""
    client = TestClient(app)
    
    response = client.get("/api/config")
    assert response.status_code == 200
    
    config = ConfigSettings(**response.json())
    assert config.dark_mode_default in ["system", "light", "dark"]
    assert isinstance(config.max_pages_per_domain, int)


def test_update_config():
    """Test updating configuration."""
    client = TestClient(app)
    
    new_config = {
        "dark_mode_default": "light",
        "max_pages_per_domain": 20,
        "max_depth": 5,
        "blacklist_domains": ["spam.com"],
        "allowed_categories": ["Tech", "Finance"],
        "role_filters": ["engineer", "developer"],
        "remote_only": True
    }
    
    response = client.put("/api/config", json=new_config)
    assert response.status_code == 200
    
    config = response.json()
    assert config["dark_mode_default"] == "light"
    assert config["max_pages_per_domain"] == 20
    assert config["remote_only"] is True


def test_sse_connection():
    """Test SSE endpoint connection."""
    client = TestClient(app)
    
    # Note: Testing SSE fully requires async client
    # This just validates the endpoint exists
    with client.stream("GET", "/api/events/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


if __name__ == "__main__":
    print("Running API tests...")
    
    # Run all tests
    test_health_check()
    print("✓ Health check test passed")
    
    test_get_summary()
    print("✓ Get summary test passed")
    
    test_start_crawl_when_idle()
    print("✓ Start crawl (idle) test passed")
    
    test_start_crawl_when_running()
    print("✓ Start crawl (running) test passed")
    
    test_stop_crawl()
    print("✓ Stop crawl test passed")
    
    test_stop_crawl_when_not_running()
    print("✓ Stop crawl (not running) test passed")
    
    test_get_logs()
    print("✓ Get logs test passed")
    
    test_list_jobs_empty()
    print("✓ List jobs (empty) test passed")
    
    test_list_jobs_with_data()
    print("✓ List jobs (with data) test passed")
    
    test_list_jobs_with_query()
    print("✓ List jobs (query) test passed")
    
    test_list_jobs_remote_only()
    print("✓ List jobs (remote only) test passed")
    
    test_get_job_detail()
    print("✓ Get job detail test passed")
    
    test_get_job_not_found()
    print("✓ Get job not found test passed")
    
    test_list_domains()
    print("✓ List domains test passed")
    
    test_get_domain_detail()
    print("✓ Get domain detail test passed")
    
    test_get_domain_not_found()
    print("✓ Get domain not found test passed")
    
    test_get_config()
    print("✓ Get config test passed")
    
    test_update_config()
    print("✓ Update config test passed")
    
    test_sse_connection()
    print("✓ SSE connection test passed")
    
    print("\n✅ All tests passed!")
