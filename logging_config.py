"""
Centralized logging configuration for HubSpot Job Scraper.

Provides structured, human-readable logging optimized for Render's log viewer.
"""

import logging
import os
import sys
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that supports structured logging with 'extra' fields.
    
    Formats log records with extra context in a readable way for Render logs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Build base message
        base_msg = super().format(record)
        
        # Add extra fields if present
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName',
                'relativeCreated', 'thread', 'threadName', 'exc_info',
                'exc_text', 'stack_info', 'asctime'
            ]:
                extra_fields[key] = value
        
        # Append extra fields if any
        if extra_fields:
            extra_str = " | " + " ".join(
                f"{k}={v}" for k, v in sorted(extra_fields.items())
            )
            return base_msg + extra_str
        
        return base_msg


def setup_logging(name: str = "hubspot_scraper") -> logging.Logger:
    """
    Configure and return a logger with structured formatting.
    
    Args:
        name: Logger name (default: "hubspot_scraper")
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler for stdout (Render reads stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Use structured formatter
    formatter = StructuredFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Return named logger
    logger = logging.getLogger(name)
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
