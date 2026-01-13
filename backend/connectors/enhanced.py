"""
Enhanced Connector Interface for Unified Ingestion Pipeline.

Standardized interface for connectors to deliver raw source content
for unified ingestion (parse → chunk → embed → store).
"""

from typing import AsyncIterator, Dict, Any, Optional, Iterator
from dataclasses import dataclass
from enum import Enum
from abc import abstractmethod
from connectors.base import BaseConnector


class SourceType(str, Enum):
    """Supported source types."""
    FILE_UPLOAD = "file_upload"
    GOOGLE_DRIVE = "google_drive"
    NOTION = "notion"
    WEB = "web"
    SFTP = "sftp"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    SHAREPOINT = "sharepoint"
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


class EnhancedConnector(BaseConnector):
    """
    Enhanced connector interface for the unified ingestion pipeline.
    """
    
    @abstractmethod
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
        raise NotImplementedError("fetch_documents must be implemented by connector subclasses")

    @abstractmethod
    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Iterator[SourceDocument]:
        """
        Synchronous fetch for worker pipelines.
        """
        raise NotImplementedError("fetch_documents_sync must be implemented by connector subclasses")
    
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
