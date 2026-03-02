"""
PageIndex SDK Documents Client

Async client for document processing and management operations.
"""

import os
from datetime import datetime
from typing import Optional, List

from .config import SDKConfig
from .models import Document, DocumentMetadata, DocumentVersion

# Import persistence module directly to avoid tiktoken dependency
import importlib.util
import sys

def _get_persistence_module():
    """Load persistence module without triggering tiktoken import."""
    spec = importlib.util.spec_from_file_location(
        'persistence',
        os.path.join(os.path.dirname(__file__), '..', 'persistence.py')
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DocumentsClient:
    """Async client for document operations."""

    def __init__(self, config: SDKConfig):
        """
        Initialize DocumentsClient.

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

    async def process(
        self,
        path: str,
        tags: Optional[List[str]] = None,
        doc_type: Optional[str] = None,
        doc_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Document:
        """
        Process a PDF or Markdown document and persist to MongoDB.

        Args:
            path: Path to the PDF or Markdown file
            tags: Optional list of tags for categorization
            doc_type: Optional document type (e.g., "financial", "legal")
            doc_id: Optional existing document ID for versioning
            model: Optional model override

        Returns:
            Document with id, version, and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type not supported
        """
        # Validate file exists
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        # Detect file type
        ext = os.path.splitext(path)[1].lower()
        if ext == '.pdf':
            tree = await self._process_pdf(path, model or self._config.model)
        elif ext in ('.md', '.markdown'):
            tree = await self._process_markdown(path, model or self._config.model)
        else:
            raise ValueError(f"Unsupported file type: {ext}. Use PDF or Markdown.")

        # Create metadata
        metadata = DocumentMetadata(
            filename=os.path.basename(path),
            file_path=os.path.abspath(path),
            page_count=self._estimate_page_count(tree),
            token_count=self._estimate_token_count(tree),
            model_used=model or self._config.model,
            tags=tags or [],
            doc_type=doc_type or "",
            upload_date=datetime.utcnow(),
        )

        # Save to MongoDB
        repository = self._get_repository()
        persistence = _get_persistence_module()

        version = repository.save(
            document_id=doc_id,
            tree=tree,
            metadata=persistence.DocumentMetadata(
                filename=metadata.filename,
                file_path=metadata.file_path,
                upload_date=metadata.upload_date,
                page_count=metadata.page_count,
                token_count=metadata.token_count,
                model_used=metadata.model_used,
                processing_version=f"sdk-{metadata.model_used}",
                tags=metadata.tags,
                doc_type=metadata.doc_type,
            )
        )

        return Document(
            id=version.document_id,
            version=version.version,
            metadata=metadata,
            tree=None,  # Don't return tree by default
            created_at=version.created_at,
        )

    async def _process_pdf(self, path: str, model: str) -> dict:
        """Process PDF file using existing page_index module."""
        # Load page_index module
        spec = importlib.util.spec_from_file_location(
            'page_index',
            os.path.join(os.path.dirname(__file__), '..', 'page_index.py')
        )
        page_index = importlib.util.module_from_spec(spec)

        # Mock tiktoken for import
        sys.modules['tiktoken'] = type(sys)('tiktoken')

        spec.loader.exec_module(page_index)

        # Create config
        opt = page_index.config(model=model)

        # Process PDF
        return page_index.page_index_main(path, opt)

    async def _process_markdown(self, path: str, model: str) -> dict:
        """Process Markdown file using existing page_index_md module."""
        import asyncio

        spec = importlib.util.spec_from_file_location(
            'page_index_md',
            os.path.join(os.path.dirname(__file__), '..', 'page_index_md.py')
        )
        page_index_md = importlib.util.module_from_spec(spec)

        # Mock tiktoken for import
        if 'tiktoken' not in sys.modules:
            sys.modules['tiktoken'] = type(sys)('tiktoken')

        spec.loader.exec_module(page_index_md)

        return await page_index_md.md_to_tree(md_path=path, model=model)

    def _estimate_page_count(self, tree: dict) -> int:
        """Estimate page count from tree structure."""
        if not tree:
            return 0

        def get_max_page(node):
            max_page = node.get('end_index', 0) or 0
            for child in node.get('nodes', []):
                max_page = max(max_page, get_max_page(child))
            return max_page

        if isinstance(tree, list):
            return max(get_max_page(node) for node in tree) if tree else 0
        return get_max_page(tree)

    def _estimate_token_count(self, tree: dict) -> int:
        """Estimate token count from tree structure."""
        if not tree:
            return 0

        def count_tokens(node):
            count = 0
            if node.get('title'):
                count += len(node['title'].split()) * 1.3
            if node.get('summary'):
                count += len(node['summary'].split()) * 1.3
            if node.get('text'):
                count += len(node['text'].split()) * 1.3
            for child in node.get('nodes', []):
                count += count_tokens(child)
            return int(count)

        if isinstance(tree, list):
            return sum(count_tokens(node) for node in tree)
        return count_tokens(tree)

    async def get(self, doc_id: str, include_tree: bool = False) -> Optional[Document]:
        """
        Get a document by ID.

        Args:
            doc_id: Document ID
            include_tree: Whether to include the tree structure

        Returns:
            Document or None if not found
        """
        repository = self._get_repository()
        version = repository.get_latest(doc_id)

        if version is None:
            return None

        return Document.from_version(
            DocumentVersion.from_dict({
                'document_id': version.document_id,
                'version': version.version,
                'created_at': version.created_at,
                'is_latest': version.is_latest,
                'metadata': {
                    'filename': version.metadata.filename,
                    'file_path': version.metadata.file_path,
                    'page_count': version.metadata.page_count,
                    'token_count': version.metadata.token_count,
                    'model_used': version.metadata.model_used,
                    'tags': version.metadata.tags,
                    'doc_type': version.metadata.doc_type,
                    'upload_date': version.metadata.upload_date,
                },
                'tree': version.tree,
            }),
            include_tree=include_tree
        )

    async def list(
        self,
        filename: Optional[str] = None,
        tags: Optional[List[str]] = None,
        doc_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Document]:
        """
        List documents with optional filters.

        Args:
            filename: Filter by filename (partial match)
            tags: Filter by tags (document must have ALL tags)
            doc_type: Filter by document type
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        repository = self._get_repository()
        versions = repository.find_by_metadata(
            filename=filename,
            tags=tags,
            doc_type=doc_type,
            limit=limit,
        )

        return [
            Document.from_version(
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
                    'tree': {},
                }),
                include_tree=False
            )
            for v in versions
        ]

    async def delete(self, doc_id: str) -> bool:
        """
        Delete a document and all its versions.

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        repository = self._get_repository()
        deleted_count = repository.delete_document(doc_id)
        return deleted_count > 0
