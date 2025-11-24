#!/usr/bin/env python3
"""
Integration test script for Supabase database service.

This script demonstrates how the database service works and can be used
to verify the integration without requiring an actual scraper run.

Usage:
    # Without Supabase (testing graceful degradation):
    python3 test_integration.py

    # With Supabase:
    export SUPABASE_URL="https://your-project.supabase.co"
    export SUPABASE_KEY="your-service-role-key"
    python3 test_integration.py
"""

import sys
from datetime import datetime
from uuid import uuid4

from db_service import DatabaseService
from supabase_client import SupabaseClient


def test_database_service():
    """Test the database service integration."""
    
    print("=" * 60)
    print("Supabase Integration Test")
    print("=" * 60)
    print()
    
    # Check if Supabase is configured
    if not SupabaseClient.is_configured():
        print("⚠️  Supabase is not configured")
        print("   Set SUPABASE_URL and SUPABASE_KEY environment variables")
        print("   to test with actual database connection.")
        print()
        print("✅ Testing graceful degradation (no database)...")
        print()
    else:
        print("✅ Supabase is configured")
        print(f"   URL: {SupabaseClient._url}")
        print("   Key: ****" + SupabaseClient._key[-4:] if SupabaseClient._key else "")
        print()
    
    # Create database service
    db_service = DatabaseService()
    print(f"Database Service Enabled: {db_service.enabled}")
    print()
    
    # Test 1: Create scrape run
    print("Test 1: Creating scrape run...")
    scrape_run_id = db_service.create_scrape_run()
    if scrape_run_id:
        print(f"✅ Created scrape run: {scrape_run_id}")
    else:
        print("⚠️  Scrape run not created (database not configured)")
    print()
    
    # Test 2: Create/get company
    print("Test 2: Creating/getting company...")
    company_id = db_service.get_or_create_company(
        name="Test Company Inc.",
        domain="testcompany.com",
        source_url="https://testcompany.com",
        logo_url="https://testcompany.com/logo.png"
    )
    if company_id:
        print(f"✅ Company ID: {company_id}")
    else:
        print("⚠️  Company not created (database not configured)")
    print()
    
    # Test 3: Create/get job
    if company_id:
        print("Test 3: Creating/getting job...")
        job_data = {
            "title": "Senior Software Engineer",
            "url": "https://testcompany.com/jobs/senior-engineer",
            "department": "Engineering",
            "location": "San Francisco, CA",
            "remote_type": "hybrid",
            "description": "We are looking for a senior software engineer...",
            "ats": "greenhouse",
            "seniority": "senior",
            "employment_type": "full_time",
            "technologies": ["Python", "PostgreSQL", "React"]
        }
        
        job_result = db_service.get_or_create_job(
            company_id=company_id,
            job_title=job_data["title"],
            job_url=job_data["url"],
            department=job_data["department"],
            location=job_data["location"],
            remote_type=job_data["remote_type"],
            description=job_data["description"],
            ats_provider=job_data["ats"]
        )
        
        if job_result:
            job_id, is_new = job_result
            print(f"✅ Job ID: {job_id}")
            print(f"   Is New: {is_new}")
            
            # Test 4: Insert job metadata
            print()
            print("Test 4: Inserting job metadata...")
            metadata_result = db_service.insert_job_metadata(
                job_id=job_id,
                seniority=job_data["seniority"],
                employment_type=job_data["employment_type"],
                technologies=job_data["technologies"],
                raw_json=job_data
            )
            if metadata_result:
                print("✅ Job metadata inserted")
            else:
                print("⚠️  Job metadata not inserted")
            
            # Test 5: Insert ATS source
            print()
            print("Test 5: Inserting ATS source...")
            ats_result = db_service.insert_ats_source(
                job_id=job_id,
                provider=job_data["ats"]
            )
            if ats_result:
                print("✅ ATS source inserted")
            else:
                print("⚠️  ATS source not inserted")
            
            # Test 6: Insert job history
            print()
            print("Test 6: Inserting job history...")
            history_result = db_service.insert_job_history(
                job_id=job_id,
                snapshot=job_data
            )
            if history_result:
                print("✅ Job history inserted")
            else:
                print("⚠️  Job history not inserted")
        else:
            print("⚠️  Job not created (database not configured)")
    else:
        print("⚠️  Skipping job tests (no company ID)")
    
    # Test 7: Update scrape run
    if scrape_run_id:
        print()
        print("Test 7: Updating scrape run...")
        update_result = db_service.update_scrape_run(
            run_id=scrape_run_id,
            total_companies=1,
            total_jobs=1,
            errors=None
        )
        if update_result:
            print("✅ Scrape run updated")
        else:
            print("⚠️  Scrape run not updated")
    
    # Test 8: Save complete job using convenience method
    print()
    print("Test 8: Saving complete job using save_scraped_job...")
    complete_job_id = db_service.save_scraped_job(
        company_name="Another Test Company",
        company_domain="anothertest.com",
        company_source_url="https://anothertest.com",
        job_data={
            "title": "DevOps Engineer",
            "url": "https://anothertest.com/jobs/devops",
            "department": "Operations",
            "location": "Remote",
            "remote_type": "remote",
            "summary": "We need a DevOps engineer...",
            "ats": "lever",
            "seniority": "mid",
            "employment_type": "full_time",
            "technologies": ["Docker", "Kubernetes", "AWS"]
        },
        save_history=True
    )
    if complete_job_id:
        print(f"✅ Complete job saved: {complete_job_id}")
    else:
        print("⚠️  Complete job not saved (database not configured)")
    
    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)
    
    if not db_service.enabled:
        print()
        print("💡 Tip: Configure Supabase to test with actual database:")
        print("   export SUPABASE_URL='https://your-project.supabase.co'")
        print("   export SUPABASE_KEY='your-service-role-key'")
    else:
        print()
        print("✅ Database integration is working!")
        print("   Check your Supabase dashboard to see the data.")


if __name__ == "__main__":
    try:
        test_database_service()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
