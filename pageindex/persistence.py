"""
PageIndex MongoDB Persistence Module

Provides document versioning and metadata querying for processed document trees.
"""

import os
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure


@dataclass
class DocumentMetadata:
    """Metadata for a processed document."""
    filename: str
    file_path: str
    upload_date: datetime
    page_count: int
    token_count: int
    model_used: str
    processing_version: str
    tags: List[str] = field(default_factory=list)
    doc_type: str = ""


@dataclass
class DocumentVersion:
    """A versioned document with tree structure and metadata."""
    document_id: str
    version: int
    created_at: datetime
    is_latest: bool
    tree: Dict[str, Any]
    metadata: DocumentMetadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format."""
        return {
            "document_id": self.document_id,
            "version": self.version,
            "created_at": self.created_at,
            "is_latest": self.is_latest,
            "tree": self.tree,
            "metadata": asdict(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentVersion":
        """Create from MongoDB document."""
        metadata = DocumentMetadata(**data["metadata"])
        return cls(
            document_id=data["document_id"],
            version=data["version"],
            created_at=data["created_at"],
            is_latest=data["is_latest"],
            tree=data["tree"],
            metadata=metadata
        )


def get_mongo_client(uri: Optional[str] = None) -> MongoClient:
    """
    Get MongoDB client connection.

    Args:
        uri: MongoDB connection URI. Defaults to MONGODB_URI env var
             or mongodb://localhost:27017

    Returns:
        MongoClient instance

    Raises:
        ConnectionFailure: If cannot connect to MongoDB
    """
    if uri is None:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    # Test connection
    try:
        client.admin.command('ping')
    except ConnectionFailure as e:
        raise ConnectionFailure(f"Cannot connect to MongoDB at {uri}: {e}")

    return client


def generate_document_id() -> str:
    """Generate a unique document ID."""
    return str(uuid.uuid4())


class PageIndexRepository:
    """
    Repository for storing and retrieving processed document trees
    with versioning support.
    """

    def __init__(self, client: Optional[MongoClient] = None, db_name: str = "pageindex"):
        """
        Initialize repository.

        Args:
            client: MongoDB client. If None, creates one using get_mongo_client()
            db_name: Database name (default: pageindex)
        """
        self._client = client or get_mongo_client()
        self._db = self._client[db_name]
        self._collection: Collection = self._db["documents"]

    def _get_collection(self) -> Collection:
        """Get the documents collection, creating indexes if needed."""
        # Ensure indexes
        self._collection.create_index([("document_id", 1), ("version", -1)], unique=True)
        self._collection.create_index([("document_id", 1), ("is_latest", 1)])
        self._collection.create_index([("metadata.filename", 1)])
        self._collection.create_index([("metadata.tags", 1)])
        self._collection.create_index([("created_at", -1)])
        return self._collection

    def save(
        self,
        document_id: Optional[str],
        tree: Dict[str, Any],
        metadata: DocumentMetadata
    ) -> DocumentVersion:
        """
        Save a document version.

        If document_id is provided and exists, creates a new version.
        If document_id is None, creates a new document with a generated ID.

        Args:
            document_id: Existing document ID or None for new document
            tree: The processed tree structure
            metadata: Document metadata

        Returns:
            The created DocumentVersion
        """
        collection = self._get_collection()

        # Generate document_id if not provided
        if document_id is None:
            document_id = generate_document_id()
            version_num = 1
        else:
            # Find the latest version for this document
            latest = collection.find_one(
                {"document_id": document_id, "is_latest": True},
                sort=[("version", -1)]
            )
            if latest:
                version_num = latest["version"] + 1
                # Mark previous version as not latest
                collection.update_many(
                    {"document_id": document_id},
                    {"$set": {"is_latest": False}}
                )
            else:
                version_num = 1

        # Create new version
        doc_version = DocumentVersion(
            document_id=document_id,
            version=version_num,
            created_at=datetime.utcnow(),
            is_latest=True,
            tree=tree,
            metadata=metadata
        )

        collection.insert_one(doc_version.to_dict())
        return doc_version

    def get_latest(self, document_id: str) -> Optional[DocumentVersion]:
        """
        Get the latest version of a document.

        Args:
            document_id: The document ID

        Returns:
            DocumentVersion or None if not found
        """
        collection = self._get_collection()
        doc = collection.find_one(
            {"document_id": document_id, "is_latest": True}
        )
        return DocumentVersion.from_dict(doc) if doc else None

    def get_version(self, document_id: str, version_num: int) -> Optional[DocumentVersion]:
        """
        Get a specific version of a document.

        Args:
            document_id: The document ID
            version_num: The version number

        Returns:
            DocumentVersion or None if not found
        """
        collection = self._get_collection()
        doc = collection.find_one(
            {"document_id": document_id, "version": version_num}
        )
        return DocumentVersion.from_dict(doc) if doc else None

    def find_by_metadata(
        self,
        filename: Optional[str] = None,
        tags: Optional[List[str]] = None,
        doc_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DocumentVersion]:
        """
        Find documents by metadata criteria.

        Only returns latest versions (is_latest=True).

        Args:
            filename: Filter by filename (partial match)
            tags: Filter by tags (document must have ALL specified tags)
            doc_type: Filter by document type
            date_from: Filter documents created on or after this date
            date_to: Filter documents created on or before this date
            limit: Maximum number of results

        Returns:
            List of matching DocumentVersion objects
        """
        collection = self._get_collection()
        query: Dict[str, Any] = {"is_latest": True}

        if filename:
            query["metadata.filename"] = {"$regex": filename, "$options": "i"}

        if tags:
            query["metadata.tags"] = {"$all": tags}

        if doc_type:
            query["metadata.doc_type"] = doc_type

        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            query["created_at"] = date_query

        cursor = collection.find(query).sort("created_at", -1).limit(limit)
        return [DocumentVersion.from_dict(doc) for doc in cursor]

    def list_versions(self, document_id: str) -> List[DocumentVersion]:
        """
        List all versions of a document.

        Args:
            document_id: The document ID

        Returns:
            List of DocumentVersion objects, sorted by version descending
        """
        collection = self._get_collection()
        cursor = collection.find(
            {"document_id": document_id}
        ).sort("version", -1)
        return [DocumentVersion.from_dict(doc) for doc in cursor]

    def delete_document(self, document_id: str) -> int:
        """
        Delete all versions of a document.

        Args:
            document_id: The document ID

        Returns:
            Number of documents deleted
        """
        collection = self._get_collection()
        result = collection.delete_many({"document_id": document_id})
        return result.deleted_count
