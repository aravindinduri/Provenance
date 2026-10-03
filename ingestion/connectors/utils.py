"""
URL canonicalization and content hashing utilities for ingestion.
Architecture reference: §F.3 (Idempotency and Deduplication).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Query parameters to strip during URL canonicalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "mc_eid",
    "_hsenc",
    "_hsmi",
    "ref",
    "source",
}


def canonicalize_url(url: str | None) -> str | None:
    """
    Canonicalizes a URL per architecture §F.3:
      - Lowercase scheme and host
      - Strip tracking query parameters (utm_*, fbclid, gclid, etc.)
      - Drop fragments (#...)
      - Drop trailing slash from path (except root '/')
      - Sort remaining query parameters
    """
    if not url:
        return None

    url_str = url.strip()
    if not url_str:
        return None

    try:
        parsed = urlparse(url_str)
    except Exception:
        return url_str

    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower() if parsed.netloc else ""

    # Path normalization: collapse multiple slashes, remove trailing slash if not root
    path = parsed.path
    if path and path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Query params: filter out tracking params and sort
    query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
    filtered_query = sorted(
        (k, v) for k, v in query_tuples if k.lower() not in TRACKING_PARAMS
    )
    new_query = urlencode(filtered_query)

    # Fragment dropped per §F.3
    fragment = ""

    return urlunparse((scheme, netloc, path, parsed.params, new_query, fragment))


def compute_content_hash(data: Any) -> str:
    """
    Computes a deterministic SHA-256 hexadecimal hash over data.
    If dict or list, uses canonical JSON with sorted keys.
    """
    if isinstance(data, (dict, list)):
        payload_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    elif isinstance(data, bytes):
        payload_bytes = data
    else:
        payload_bytes = str(data).encode("utf-8")

    return hashlib.sha256(payload_bytes).hexdigest()
