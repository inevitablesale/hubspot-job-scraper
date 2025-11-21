import re
from urllib.parse import urlparse


def normalize_domain(value: str) -> str:
    """Normalize a URL or domain into bare domain.

    Returns empty string when invalid.
    """
    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"https://{value}"
    try:
        parsed = urlparse(value)
    except Exception:
        return ""
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    # basic host validation
    if not re.match(r"^[a-z0-9.-]+$", host):
        return ""
    return host
