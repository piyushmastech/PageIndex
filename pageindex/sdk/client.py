"""
PageIndex SDK Main Client

Main entry point for the PageIndex SDK.
"""

from typing import Optional

from .config import SDKConfig, load_config
from .documents import DocumentsClient
from .versions import VersionsClient


class PageIndex:
    """
    PageIndex SDK Client.

    Main entry point for document processing, retrieval, and management.

    Example:
        >>> from pageindex import PageIndex
        >>> client = PageIndex()
        >>> doc = await client.documents.process("/path/to/doc.pdf")
        >>> result = await client.query.search("What is revenue?", doc.id)
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize PageIndex client.

        Configuration is loaded from:
        1. Provided config dict (overrides)
        2. Environment variables (PAGEINDEX_*)
        3. .env file (PAGEINDEX_*)

        Args:
            config: Optional configuration overrides

        Example:
            >>> # Auto-load from .env
            >>> client = PageIndex()
            >>>
            >>> # Override specific settings
            >>> client = PageIndex({"model": "gpt-4o-mini"})
        """
        self._config = load_config(config)
        self._documents: Optional[DocumentsClient] = None
        self._versions: Optional[VersionsClient] = None
        self._query = None  # Initialized in Task 3

    @property
    def config(self) -> SDKConfig:
        """Get SDK configuration."""
        return self._config

    @property
    def documents(self) -> DocumentsClient:
        """Get documents client for processing and management."""
        if self._documents is None:
            self._documents = DocumentsClient(self._config)
        return self._documents

    @property
    def versions(self) -> VersionsClient:
        """Get versions client for version management."""
        if self._versions is None:
            self._versions = VersionsClient(self._config)
        return self._versions

    @property
    def query(self):
        """Get query client for retrieval operations."""
        if self._query is None:
            from .query import QueryClient
            self._query = QueryClient(self._config)
        return self._query

    def close(self):
        """Close connections and cleanup resources."""
        # Cleanup is handled by garbage collection for now
        self._documents = None
        self._versions = None
        self._query = None

    async def __aenter__(self) -> "PageIndex":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()
