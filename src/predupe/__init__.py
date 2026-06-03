"""predupe — find near-duplicate documents before you embed them."""

from __future__ import annotations

from .cluster import Cluster, cluster_documents
from .scan import ScanResult, scan

__version__ = "0.1.0"
__all__ = ["scan", "ScanResult", "cluster_documents", "Cluster", "__version__"]
