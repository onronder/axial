"""
Enhanced Connector Interface for Unified Ingestion Pipeline.

This extends the existing BaseConnector with a new standardized interface
for the unified ingestion pipeline while maintaining backward compatibility.
"""

from typing import AsyncIterator, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from connectors.base import BaseConnector as LegacyBaseConnector, ConnectorDocument


class SourceType(str, Enum):
    """Supported source types."""
    FILE_UPLOAD = "file_upload"
    GOOGLE_DRIVE = "google_drive"
    NOTION = "notion"
    WEB = "web"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    SLACK = "slack"


@dataclass
class SourceDocument:
    """
    Standardized document from any source for the unified pipeline.
    
    This is the new contract between connectors and the ingestion pipeline.
    """
    content: bytes | str
    """Raw content (bytes for binary files, str for text)"""
    
    metadata: Dict[str, Any]
    """Source-specific metadata (URLs, IDs, timestamps, etc.)"""
    
    source_type: SourceType
    """Type of source this document came from"""
    
    source_id: str
    """Unique identifier in the source system"""
    
    filename: str
    """Display name for the document"""
    
    mime_type: str
    """MIME type of the content"""
    
    size_bytes: int
    """Size of content in bytes"""
    
    parent_id: Optional[str] = None
    """Optional parent document ID (for hierarchical sources)"""
    
    def to_connector_document(self) -> ConnectorDocument:
        """Convert to legacy ConnectorDocument format."""
        content_str = self.content if isinstance(self.content, str) else self.content.decode('utf-8', errors='ignore')
        return ConnectorDocument(
            page_content=content_str,
            metadata=self.metadata
        )


class ConnectorError(Exception):
    """Base exception for connector errors."""
    pass


class AuthenticationError(ConnectorError):
    """Raised when authentication fails."""
    pass


class QuotaExceededError(ConnectorError):
    """Raised when source quota is exceeded."""
    pass


class ItemNotFoundError(ConnectorError):
    """Raised when requested item doesn't exist."""
    pass


class FileTooLargeError(ConnectorError):
    """Raised when file exceeds size limit."""
    pass


class EnhancedConnector(LegacyBaseConnector):
    """
    Enhanced connector interface for the unified ingestion pipeline.
    
    New connectors should implement fetch_documents() instead of ingest().
    The pipeline will handle all processing (parsing, chunking, embedding, storage).
    
    Backward Compatibility:
    - Still supports legacy ingest() method
    - Can be used with existing connectors
    """
    
    async def fetch_documents(
        self, 
        item_ids: list[str], 
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """
        Fetch raw documents from the source (NEW INTERFACE).
        
        This is the preferred method for new connectors.
        It returns SourceDocument objects with raw content.
        
        Args:
            item_ids: List of items to fetch
            credentials: Optional authentication credentials
            **kwargs: Connector-specific options
            
        Yields:
            SourceDocument instances with raw content
            
        Raises:
            AuthenticationError: Invalid credentials
            QuotaExceededError: Source quota exceeded
            ItemNotFoundError: Item doesn't exist
            ConnectorError: Other fetch failures
        """
        # Default implementation: convert from legacy ingest()
        config = {
            "user_id": kwargs.get("user_id"),
            "item_ids": item_ids,
            "credentials": credentials,
            "provider": self.connector_type.value if hasattr(self, 'connector_type') else "unknown"
        }
        
        async for doc in self.ingest(config):
            # Convert ConnectorDocument to SourceDocument
            yield SourceDocument(
                content=doc.page_content,
                metadata=doc.metadata,
                source_type=SourceType(config["provider"]),
                source_id=doc.metadata.get("source_id", "unknown"),
                filename=doc.metadata.get("title", "untitled"),
                mime_type=doc.metadata.get("mime_type", "text/plain"),
                size_bytes=len(doc.page_content.encode('utf-8'))
            )
    
    @property
    def connector_type(self) -> SourceType:
        """Return the connector type identifier."""
        raise NotImplementedError("Subclasses must implement connector_type")
    
    @property
    def supports_batch_fetch(self) -> bool:
        """Whether this connector can efficiently fetch multiple items at once."""
        return False
    
    @property
    def supports_incremental_sync(self) -> bool:
        """Whether this connector supports incremental syncing."""
        return False
