"""
Connector registry.
Maps source_key to the corresponding SourceConnector implementation.
"""

from __future__ import annotations

from typing import Type

from ingestion.connectors.base import SourceConnector
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
from ingestion.connectors.uk_ofsi import UKOFSIConnector
from ingestion.connectors.un_sanctions import UNSanctionsConnector

CONNECTOR_CLASSES: dict[str, Type[SourceConnector]] = {
    # 9 Tier-1 MVP Connectors
    "ofac_sls": OFACConnector,
    "gleif": GLEIFConnector,
    "gdelt_doc": GDELTConnector,
    "federal_register": FederalRegisterConnector,
    "eurlex": EURLexConnector,
    "eu_sanctions": EUSanctionsConnector,
    "un_sanctions": UNSanctionsConnector,
    "uk_ofsi": UKOFSIConnector,
    "data_gov_in": DataGovInConnector,
    # Supplementary / Tier-2
    "dgft_html": DGFTHtmlConnector,
    "cbic_html": CBICHtmlConnector,
    "cached_snapshots": CachedSnapshotsConnector,
}


def get_connector(source_key: str, **kwargs) -> SourceConnector:
    """Instantiates and returns the connector for the given source_key."""
    connector_cls = CONNECTOR_CLASSES.get(source_key)
    if not connector_cls:
        raise ValueError(f"Unknown data source connector key: {source_key!r}")
    return connector_cls(**kwargs)


def list_registered_connectors() -> list[str]:
    """Returns all registered source keys."""
    return list(CONNECTOR_CLASSES.keys())
