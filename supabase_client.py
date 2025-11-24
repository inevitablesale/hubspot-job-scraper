"""
Supabase client configuration and initialization.

This module provides a singleton Supabase client instance that can be
imported and used throughout the application.
"""

import os
from typing import Optional
from supabase import create_client, Client
from logging_config import get_logger

logger = get_logger(__name__)


class SupabaseClient:
    """Singleton Supabase client manager."""
    
    _instance: Optional[Client] = None
    _url: Optional[str] = None
    _key: Optional[str] = None
    
    @classmethod
    def initialize(cls, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize the Supabase client.
        
        Args:
            url: Supabase project URL (defaults to SUPABASE_URL env var)
            key: Supabase service role key (defaults to SUPABASE_KEY env var)
        """
        cls._url = url or os.getenv("SUPABASE_URL")
        cls._key = key or os.getenv("SUPABASE_KEY")
        
        if not cls._url or not cls._key:
            logger.warning(
                "Supabase credentials not configured. "
                "Set SUPABASE_URL and SUPABASE_KEY environment variables."
            )
            cls._instance = None
            return
        
        try:
            cls._instance = create_client(cls._url, cls._key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            cls._instance = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """
        Get the Supabase client instance.
        
        Returns:
            Supabase client or None if not initialized
        """
        if cls._instance is None:
            cls.initialize()
        return cls._instance
    
    @classmethod
    def is_configured(cls) -> bool:
        """
        Check if Supabase is properly configured.
        
        Returns:
            True if Supabase client is available, False otherwise
        """
        return cls.get_client() is not None


# Initialize on module import
SupabaseClient.initialize()


def get_supabase_client() -> Optional[Client]:
    """
    Convenience function to get the Supabase client.
    
    Returns:
        Supabase client or None if not configured
    """
    return SupabaseClient.get_client()
