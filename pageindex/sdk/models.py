"""
PageIndex SDK Data Models

Dataclasses for SDK request/response objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class DocumentMetadata:
    """Metadata for a processed document."""
    filename: str
    file_path: str
    page_count: int
    token_count: int
    model_used: str
    tags: List[str] = field(default_factory=list)
    doc_type: str = ""
    upload_date: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentMetadata":
        """Create from dictionary."""
        return cls(
            filename=data.get("filename", ""),
            file_path=data.get("file_path", ""),
            page_count=data.get("page_count", 0),
            token_count=data.get("token_count", 0),
            model_used=data.get("model_used", ""),
            tags=data.get("tags", []),
            doc_type=data.get("doc_type", ""),
            upload_date=data.get("upload_date"),
        )


@dataclass
class Document:
    """A processed document with metadata."""
    id: str
    version: int
    metadata: DocumentMetadata
    tree: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_version(cls, version: "DocumentVersion", include_tree: bool = True) -> "Document":
        """Create Document from DocumentVersion."""
        return cls(
            id=version.document_id,
            version=version.version,
            metadata=version.metadata,
            tree=version.tree if include_tree else None,
            created_at=version.created_at,
        )


@dataclass
class DocumentVersion:
    """A versioned snapshot of a document."""
    document_id: str
    version: int
    created_at: datetime
    is_latest: bool
    metadata: DocumentMetadata
    tree: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentVersion":
        """Create from dictionary (MongoDB document)."""
        metadata = DocumentMetadata.from_dict(data.get("metadata", {}))
        return cls(
            document_id=data.get("document_id", ""),
            version=data.get("version", 1),
            created_at=data.get("created_at"),
            is_latest=data.get("is_latest", True),
            metadata=metadata,
            tree=data.get("tree", {}),
        )


@dataclass
class SourceCitation:
    """A source citation from retrieval."""
    node_id: str
    title: str
    page_range: Optional[str] = None
    text_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "title": self.title,
            "page_range": self.page_range,
            "text_snippet": self.text_snippet,
        }


@dataclass
class QueryResult:
    """Result of a query/retrieval operation."""
    question: str
    answer: str
    sources: List[SourceCitation]
    doc_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "doc_id": self.doc_id,
        }


@dataclass
class SearchResult:
    """Result of document search/list operations."""
    documents: List[Document]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "documents": [
                {"id": d.id, "version": d.version, "metadata": d.metadata}
                for d in self.documents
            ],
            "total": self.total,
        }
