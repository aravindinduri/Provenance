"""
Connectors package.
Exports SourceConnector protocol, NewsConnector, and all connector classes.
"""

from ingestion.connectors.base import (
    FetchResult,
    NewsConnector,
    NormalizedRecord,
    SourceConnector,
)
from ingestion.connectors.cached_snapshots import CachedSnapshotsConnector
from ingestion.connectors.cbic_html import CBICHtmlConnector
from ingestion.connectors.data_gov_in import DataGovInConnector
from ingestion.connectors.dgft_html import DGFTHtmlConnector
from ingestion.connectors.eu_sanctions import EUSanctionsConnector
from ingestion.connectors.eurlex import EURLexConnector
from ingestion.connectors.federal_register import FederalRegisterConnector
from ingestion.connectors.gdelt import GDELTConnector
from ingestion.connectors.gleif import GLEIFConnector
from ingestion.connectors.ofac import OFACConnector
from ingestion.connectors.rate_limiter import (
    RateLimitCooldownError,
    TokenBucketRateLimiter,
    get_token_bucket_limiter,
)
from ingestion.connectors.registry import (
    CONNECTOR_CLASSES,
    get_connector,
    list_registered_connectors,
)
from ingestion.connectors.uk_ofsi import UKOFSIConnector
from ingestion.connectors.un_sanctions import UNSanctionsConnector
from ingestion.connectors.utils import canonicalize_url, compute_content_hash

__all__ = [
    "SourceConnector",
    "NewsConnector",
    "FetchResult",
    "NormalizedRecord",
    "OFACConnector",
    "GLEIFConnector",
    "GDELTConnector",
    "FederalRegisterConnector",
    "EURLexConnector",
    "EUSanctionsConnector",
    "UNSanctionsConnector",
    "UKOFSIConnector",
    "DataGovInConnector",
    "DGFTHtmlConnector",
    "CBICHtmlConnector",
    "CachedSnapshotsConnector",
    "TokenBucketRateLimiter",
    "RateLimitCooldownError",
    "get_token_bucket_limiter",
    "canonicalize_url",
    "compute_content_hash",
    "get_connector",
    "list_registered_connectors",
    "CONNECTOR_CLASSES",
]
