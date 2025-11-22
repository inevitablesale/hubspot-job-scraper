#!/usr/bin/env python3
"""
Demonstration script showing content filtering in action.

This script shows how the extractors now properly filter out
header/footer/nav content while extracting real job postings.
"""

from extractors import MultiLayerExtractor


def demo_filtering():
    """Demonstrate the filtering capabilities."""
    
    # Realistic career page HTML with header, footer, nav, and job listings
    html = '''
    <html>
    <head>
        <title>Careers - ACME Marketing Agency</title>
    </head>
    <body>
        <!-- HEADER NAVIGATION (should be filtered) -->
        <header>
            <nav class="main-navigation">
                <a href="/">Home</a>
                <a href="/about">About Us</a>
                <a href="/team">Meet Our Team</a>
                <a href="/services">Our Services</a>
                <a href="/blog">Blog</a>
                <a href="/contact">Contact</a>
                <a href="/careers" class="active">Careers</a>
            </nav>
        </header>
        
        <!-- MAIN CONTENT (should extract jobs) -->
        <main>
            <section class="hero">
                <h1>Join Our Team</h1>
                <p>We're always looking for talented individuals to join our growing team.</p>
            </section>
            
            <section class="job-listings">
                <h2>Open Positions</h2>
                
                <div class="job-card">
                    <h3><a href="/jobs/senior-developer">Senior HubSpot Developer</a></h3>
                    <p class="description">We're looking for an experienced HubSpot developer to join our team...</p>
                    <p class="location">Remote (US)</p>
                </div>
                
                <div class="job-card">
                    <h3><a href="/jobs/marketing-consultant">Marketing Consultant</a></h3>
                    <p class="description">Help our clients develop and execute comprehensive marketing strategies...</p>
                    <p class="location">New York, NY</p>
                </div>
                
                <div class="job-card">
                    <h3><a href="/jobs/solutions-architect">Solutions Architect</a></h3>
                    <p class="description">Design and implement HubSpot solutions for enterprise clients...</p>
                    <p class="location">Remote</p>
                </div>
            </section>
            
            <!-- This should be filtered as it's a blog link -->
            <section class="blog-cta">
                <h3>Latest from Our Blog</h3>
                <a href="/blog/what-is-inbound-marketing">What Is Inbound Marketing?</a>
                <a href="/blog/hubspot-tips">10 HubSpot Tips Every Marketing Manager Should Know</a>
            </section>
        </main>
        
        <!-- SIDEBAR (should be filtered) -->
        <aside class="sidebar">
            <h4>Quick Links</h4>
            <ul>
                <li><a href="/resources">Resources</a></li>
                <li><a href="/case-studies">Case Studies</a></li>
                <li><a href="/podcast">Our Podcast</a></li>
            </ul>
        </aside>
        
        <!-- FOOTER (should be filtered) -->
        <footer>
            <div class="footer-nav">
                <div class="footer-column">
                    <h4>Company</h4>
                    <ul>
                        <li><a href="/about">About Us</a></li>
                        <li><a href="/team">Our Team</a></li>
                        <li><a href="/contact">Contact</a></li>
                        <li><a href="/privacy">Privacy Policy</a></li>
                    </ul>
                </div>
                
                <div class="footer-column">
                    <h4>Connect</h4>
                    <ul>
                        <li><a href="https://facebook.com/acme">Facebook</a></li>
                        <li><a href="https://twitter.com/acme">Twitter</a></li>
                        <li><a href="https://linkedin.com/company/acme">LinkedIn</a></li>
                        <li><a href="https://youtube.com/acme">YouTube</a></li>
                    </ul>
                </div>
                
                <div class="footer-column">
                    <h4>Resources</h4>
                    <ul>
                        <li><a href="/blog">Blog</a></li>
                        <li><a href="/podcast">Podcast</a></li>
                        <li><a href="/resources">Resources</a></li>
                    </ul>
                </div>
            </div>
            
            <div class="footer-bottom">
                <p>&copy; 2024 ACME Marketing Agency. All rights reserved.</p>
            </div>
        </footer>
    </body>
    </html>
    '''
    
    print("=" * 80)
    print("CONTENT FILTERING DEMONSTRATION")
    print("=" * 80)
    print()
    print("Testing extraction from a realistic careers page with:")
    print("  - Header navigation (7 links)")
    print("  - Main content with 3 job listings")
    print("  - Blog section with 2 blog posts")
    print("  - Sidebar with 3 quick links")
    print("  - Footer with 13 links (social, company, resources)")
    print()
    print("Total links in HTML: 28")
    print("Expected jobs extracted: 3 (only the job listings)")
    print()
    print("-" * 80)
    
    # Run extraction
    extractor = MultiLayerExtractor("https://acme-marketing.com")
    jobs = extractor.extract_all(html)
    
    print()
    print(f"RESULTS: Found {len(jobs)} job(s)")
    print("-" * 80)
    
    if jobs:
        for i, job in enumerate(jobs, 1):
            print(f"\nJob {i}:")
            print(f"  Title:   {job['title']}")
            print(f"  URL:     {job.get('url', 'N/A')}")
            print(f"  Summary: {job.get('summary', 'N/A')[:80]}...")
    else:
        print("\nNo jobs extracted!")
    
    print()
    print("-" * 80)
    print("VALIDATION:")
    print("-" * 80)
    
    # Validate results
    extracted_urls = [job.get('url', '') for job in jobs]
    
    # Get unique URLs (deduplication happens in scraper_engine, not in extractors)
    unique_urls = list(set(extracted_urls))
    expected_job_count = 3
    
    # Note about duplicates
    if len(jobs) > len(unique_urls):
        print(f"ℹ️  Note: Found {len(jobs)} total extractions from {len(unique_urls)} unique URLs")
        print(f"   (Multiple extractors may find the same job - deduplication happens in scraper_engine)")
        print()
    
    # Check that we got the right unique jobs
    if len(unique_urls) == expected_job_count:
        print(f"✓ Correct number of unique jobs extracted ({expected_job_count})")
    else:
        print(f"✗ Wrong number of unique jobs: expected {expected_job_count}, got {len(unique_urls)}")
    
    # Check that no header/footer links were extracted
    bad_patterns = [
        '/about', '/team', '/contact', '/services', '/blog/', 
        '/resources', '/case-studies', '/podcast', '/privacy',
        'facebook.com', 'twitter.com', 'linkedin.com', 'youtube.com'
    ]
    
    found_bad_links = []
    for url in unique_urls:
        for pattern in bad_patterns:
            if pattern in url.lower():
                found_bad_links.append((url, pattern))
    
    if not found_bad_links:
        print("✓ No header/footer/nav links extracted")
    else:
        print("✗ Found unwanted links:")
        for url, pattern in found_bad_links:
            print(f"  - {url} (matched pattern: {pattern})")
    
    # Check that job URLs were extracted
    job_patterns = ['/jobs/senior-developer', '/jobs/marketing-consultant', '/jobs/solutions-architect']
    found_job_links = [url for url in unique_urls if any(pattern in url for pattern in job_patterns)]
    
    if len(found_job_links) == expected_job_count:
        print(f"✓ All {expected_job_count} job links extracted correctly")
    else:
        print(f"✗ Only {len(found_job_links)}/{expected_job_count} job links found")
    
    print()
    print("=" * 80)
    
    # Return success status
    return (len(unique_urls) == expected_job_count and 
            not found_bad_links and 
            len(found_job_links) == expected_job_count)


if __name__ == "__main__":
    success = demo_filtering()
    
    if success:
        print("\n✅ DEMONSTRATION PASSED - Content filtering is working correctly!\n")
        exit(0)
    else:
        print("\n❌ DEMONSTRATION FAILED - See validation issues above\n")
        exit(1)
