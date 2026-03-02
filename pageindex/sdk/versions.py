"""
PageIndex SDK Versions Client

Async client for document version management operations.
"""

from typing import List, Optional

from .config import SDKConfig
from .models import DocumentVersion, DocumentMetadata

import os
import importlib.util


def _get_persistence_module():
    """Load persistence module without triggering tiktoken import."""
    spec = importlib.util.spec_from_file_location(
        'persistence',
        os.path.join(os.path.dirname(__file__), '..', 'persistence.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VersionsClient:
    """Async client for document version operations."""

    def __init__(self, config: SDKConfig):
        """
        Initialize VersionsClient.

        Args:
            config: SDK configuration
        """
        self._config = config
        self._repository = None

    def _get_repository(self):
        """Get repository instance (lazy initialization)."""
        if self._repository is None:
            persistence = _get_persistence_module()
            client = persistence.get_mongo_client(self._config.mongodb_uri)
            self._repository = persistence.PageIndexRepository(client, self._config.db_name)
        return self._repository

    async def get(self, doc_id: str, version: int, include_tree: bool = True) -> Optional[DocumentVersion]:
        """
        Get a specific version of a document.

        Args:
            doc_id: Document ID
            version: Version number
            include_tree: Whether to include the tree structure

        Returns:
            DocumentVersion or None if not found
        """
        repository = self._get_repository()
        v = repository.get_version(doc_id, version)

        if v is None:
            return None

        return DocumentVersion.from_dict({
            'document_id': v.document_id,
            'version': v.version,
            'created_at': v.created_at,
            'is_latest': v.is_latest,
            'metadata': {
                'filename': v.metadata.filename,
                'file_path': v.metadata.file_path,
                'page_count': v.metadata.page_count,
                'token_count': v.metadata.token_count,
                'model_used': v.metadata.model_used,
                'tags': v.metadata.tags,
                'doc_type': v.metadata.doc_type,
                'upload_date': v.metadata.upload_date,
            },
            'tree': v.tree if include_tree else {},
        })

    async def list(self, doc_id: str, include_trees: bool = False) -> List[DocumentVersion]:
        """
        List all versions of a document.

        Args:
            doc_id: Document ID
            include_trees: Whether to include tree structures

        Returns:
            List of DocumentVersion sorted by version descending
        """
        repository = self._get_repository()
        versions = repository.list_versions(doc_id)

        return [
            DocumentVersion.from_dict({
                'document_id': v.document_id,
                'version': v.version,
                'created_at': v.created_at,
                'is_latest': v.is_latest,
                'metadata': {
                    'filename': v.metadata.filename,
                    'file_path': v.metadata.file_path,
                    'page_count': v.metadata.page_count,
                    'token_count': v.metadata.token_count,
                    'model_used': v.metadata.model_used,
                    'tags': v.metadata.tags,
                    'doc_type': v.metadata.doc_type,
                    'upload_date': v.metadata.upload_date,
                },
                'tree': v.tree if include_trees else {},
            })
            for v in versions
        ]
