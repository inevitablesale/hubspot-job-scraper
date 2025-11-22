"""
Example script to run the enhanced API server with scraper integration.

This demonstrates how to start the API server with the new architecture.
"""

import asyncio
import logging
from pathlib import Path

# Import the API server
from api_server import app
from integration import integrate_with_existing_scraper


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scraper.log')
        ]
    )


def main():
    """
    Main entry point for running the enhanced API server.
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("HubSpot Job Scraper - Enhanced API Server")
    logger.info("="*60)
    
    # Integrate with existing scraper
    logger.info("Integrating with scraper engine...")
    integrate_with_existing_scraper()
    
    # Import uvicorn for running the server
    import uvicorn
    
    # Server configuration
    config = {
        "app": "api_server:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,  # Set to False in production
        "log_level": "info",
        "access_log": True,
    }
    
    logger.info("Starting API server on http://0.0.0.0:8000")
    logger.info("API Documentation: http://0.0.0.0:8000/docs")
    logger.info("Control Room UI: http://0.0.0.0:8000/")
    logger.info("")
    logger.info("API Endpoints:")
    logger.info("  - GET  /api/system/summary       - System status")
    logger.info("  - POST /api/crawl/start          - Start crawl")
    logger.info("  - POST /api/crawl/stop           - Stop crawl")
    logger.info("  - GET  /api/events/stream        - SSE event stream")
    logger.info("  - GET  /api/jobs                 - List jobs")
    logger.info("  - GET  /api/domains              - List domains")
    logger.info("  - GET  /api/config               - Get config")
    logger.info("  - PUT  /api/config               - Update config")
    logger.info("="*60)
    
    # Run the server
    uvicorn.run(**config)


if __name__ == "__main__":
    main()
