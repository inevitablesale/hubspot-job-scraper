# supabase_client.py
import os
from typing import Optional

from supabase import create_client, Client  # pip install supabase

_SUPABASE_CLIENT: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Returns a Supabase client if SUPABASE_URL and SUPABASE_KEY are set.
    If not set, returns None so the scraper can keep running without DB.
    """
    global _SUPABASE_CLIENT

    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    _SUPABASE_CLIENT = create_client(url, key)
    return _SUPABASE_CLIENT
